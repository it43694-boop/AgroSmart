"""
Service Vision par Ordinateur - Analyse images drones
Détecte maladies, ravageurs, anomalies
"""

import os
import json
import math
from typing import Dict, Any, List, Tuple, Optional
from io import BytesIO
import base64
import numpy as np
from PIL import Image
import structlog

import models

try:
    from ultralytics import YOLO
    import torch
    HAS_CV = True
except ImportError:
    HAS_CV = False
    print("YOLO/Torch non disponibles - mode fallback active")

from services.cache_service import cached

logger = structlog.get_logger()


class DroneImageAnalyzer:
    """Analyseur images drone pour agriculture"""

    def __init__(self):
        self.model = None
        self.device = "cpu"  # Default to CPU
        if HAS_CV:
            try:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except:
                self.device = "cpu"
        self.diseases = {
            "leaf_spot": {"severity": "high", "treatment": "Fongicide"},
            "powdery_mildew": {"severity": "medium", "treatment": "Soufre"},
            "rust": {"severity": "high", "treatment": "Fongicide"},
            "blight": {"severity": "critical", "treatment": "Isoler + Fungicide"},
            "healthy": {"severity": "none", "treatment": "Maintenance"}
        }

        if HAS_CV:
            self.load_model()

    def load_model(self):
        """Charger modèle YOLO"""
        try:
            model_path = os.getenv("CV_MODEL_PATH", "models/plant_disease_yolo.pt")
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                self.model_version = os.path.basename(model_path)
            else:
                self.model = YOLO('yolov8n.pt')
                self.model_version = 'yolov8n'
            logger.info("Modèle YOLO chargé avec succès", model=self.model_version)
        except Exception as e:
            logger.error("Erreur chargement YOLO", error=str(e))
            self.model = None
            self.model_version = "fallback"

    def analyze_image(self, image_path_or_bytes, user_id: int = None) -> Dict[str, Any]:
        """
        Analyse image drone complète

        Args:
            image_path_or_bytes: Path string ou bytes
            user_id: ID utilisateur pour logging

        Returns:
            {
                "diseases": [...],
                "severity": "high|medium|low|none",
                "heatmap": base64_image,
                "recommendations": [...],
                "confidence": 0.85
            }
        """
        try:
            # Charger image
            if isinstance(image_path_or_bytes, bytes):
                img = Image.open(BytesIO(image_path_or_bytes))
            else:
                img = Image.open(image_path_or_bytes)

            # Normaliser
            img = img.convert('RGB')
            img_array = np.array(img)

            # Mode fallback ou YOLO
            if not HAS_CV or self.model is None:
                return self._fallback_analysis(img_array)

            # Inférence YOLO
            results = self.model.predict(img_array, conf=0.3)

            # Post-processing
            detected_diseases = self._extract_diseases(results)
            severity = self._calculate_severity(detected_diseases)
            heatmap = self._generate_heatmap(results, img_array)
            recommendations = self._format_business_recommendations(detected_diseases, severity)

            return {
                "diseases": detected_diseases,
                "severity": severity,
                "heatmap": self._encode_heatmap(heatmap),
                "recommendations": recommendations,
                "confidence": float(np.mean([d["confidence"] for d in detected_diseases])) if detected_diseases else 0.5,
                "analyzed_at": __import__('datetime').datetime.utcnow().isoformat(),
                "source": "yolo",
                "model_version": getattr(self, "model_version", "unknown")
            }

        except Exception as e:
            logger.error("Erreur analyse image", error=str(e), user_id=user_id)
            return self._fallback_analysis(None)

    def _extract_diseases(self, yolo_results) -> List[Dict]:
        """Extraire maladies détectées"""
        diseases = []

        for result in yolo_results:
            if result.boxes is None:
                continue

            for box, conf in zip(result.boxes.xyxy, result.boxes.conf):
                # Classifier maladie basée sur confidence zone
                disease_name = self._classify_by_location(box, conf)
                diseases.append({
                    "type": disease_name,
                    "confidence": float(conf),
                    "location": [int(x) for x in box[:2]]
                })

        return diseases

    def _classify_by_location(self, box, conf) -> str:
        """Classifier maladie par zone"""
        # Logique simplifiée
        if conf > 0.8:
            return "blight" if conf > 0.9 else "rust"
        elif conf > 0.6:
            return "leaf_spot"
        else:
            return "powdery_mildew"

    def _calculate_severity(self, diseases: List[Dict]) -> str:
        """Calculer sévérité globale"""
        if not diseases:
            return "none"

        avg_conf = np.mean([d["confidence"] for d in diseases])

        if avg_conf > 0.85:
            return "critical"
        elif avg_conf > 0.7:
            return "high"
        elif avg_conf > 0.5:
            return "medium"
        else:
            return "low"

    def _generate_heatmap(self, results, original_img) -> np.ndarray:
        """Générer heatmap anomalies"""
        heatmap = np.zeros_like(original_img[:, :, 0], dtype=np.float32)

        for result in results:
            if result.masks is None:
                continue

            # Appliquer masques de détection
            for mask in result.masks.data:
                mask_np = mask.cpu().numpy() if hasattr(mask, 'cpu') else mask
                heatmap += mask_np.astype(np.float32)

        # Normaliser
        heatmap = np.clip(heatmap, 0, 1)
        heatmap = (heatmap * 255).astype(np.uint8)

        return heatmap

    def _encode_heatmap(self, heatmap: np.ndarray) -> str:
        """Encoder heatmap en base64"""
        try:
            img = Image.fromarray(heatmap, mode='L')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        except Exception as e:
            logger.error("Erreur encodage heatmap", error=str(e))
            return ""

    def _get_recommendations(self, diseases: List[Dict]) -> List[str]:
        """Générer recommandations traitement"""
        recommendations = []

        for disease in diseases:
            disease_type = disease["type"]
            if disease_type in self.diseases:
                info = self.diseases[disease_type]
                recommendations.append(f"{disease_type}: {info['treatment']}")

        if not recommendations:
            recommendations.append("Champs sain - continuer surveillance")

        return recommendations

    def _format_business_recommendations(self, diseases: List[Dict], severity: str) -> List[str]:
        """Format recommendations métier plus actionnables"""
        recommendations = self._get_recommendations(diseases)

        if severity in ["critical", "high"]:
            recommendations.append("Vérifier l'irrigation et appliquer un traitement immédiatement.")
        elif severity == "medium":
            recommendations.append("Planifier un contrôle dans les 2-3 jours et surveiller l'évolution.")
        else:
            recommendations.append("Maintenir une surveillance régulière du champ.")

        if not diseases:
            recommendations.append("Aucune maladie nette détectée, continuer les inspections visuelles.")

        return recommendations

    def _compute_green_ratio(self, img_array: np.ndarray) -> float:
        if img_array is None or img_array.size == 0:
            return 0.33
        img_array = img_array.astype(np.float32)
        green = np.mean(img_array[:, :, 1])
        total = np.mean(img_array.sum(axis=2))
        if total <= 0:
            return 0.33
        return float(np.clip(green / total, 0.1, 0.7))

    def _classify_by_green_ratio(self, ratio: float) -> str:
        if ratio > 0.38:
            return "healthy"
        if ratio > 0.32:
            return "powdery_mildew"
        if ratio > 0.26:
            return "leaf_spot"
        return "drought_stress"

    def _fallback_analysis(self, img_array=None) -> Dict[str, Any]:
        """Analyse fallback quand YOLO indisponible"""
        logger.warning("Mode fallback Computer Vision activé")
        green_ratio = self._compute_green_ratio(img_array)
        disease = self._classify_by_green_ratio(green_ratio)
        severity = "low" if disease == "healthy" else "medium"
        recommendations = [
            "Contrôle visuel du champ recommandé",
            "Si la couleur verte est faible, vérifier l'irrigation et la qualité du sol",
        ]
        if disease != "healthy":
            recommendations.append("Envisager un traitement fongicide ou insecticide adapté selon le symptôme observé.")

        return {
            "diseases": [{
                "type": disease,
                "confidence": float(green_ratio),
                "location": [0, 0]
            }],
            "severity": severity,
            "heatmap": "",
            "recommendations": recommendations,
            "confidence": float(green_ratio),
            "analyzed_at": __import__('datetime').datetime.utcnow().isoformat(),
            "source": "fallback",
            "fallback_mode": True
        }


# Instance globale
drone_analyzer = DroneImageAnalyzer()


def analyze_drone_image(image_data: bytes, user_id: int = None) -> Dict[str, Any]:
    """
    Fonction principale pour analyse image drone
    Utilisée par les routes API
    """
    return drone_analyzer.analyze_image(image_data, user_id)


def get_analysis_history(user_id: int, db=None) -> List[Dict[str, Any]]:
    """
    Récupérer historique analyses pour utilisateur depuis la base.
    """
    try:
        if db is None:
            from database import get_db
            db = next(get_db())

        analyses = (
            db.query(models.PlantDisease)
            .filter(models.PlantDisease.user_id == user_id)
            .order_by(models.PlantDisease.diagnosis_date.desc())
            .all()
        )

        history = []
        for record in analyses:
            recommendations = []
            try:
                recommendations = json.loads(record.recommendations) if record.recommendations else []
            except Exception:
                recommendations = [record.recommendations] if record.recommendations else []

            history.append({
                "id": record.id,
                "crop_id": record.crop_id,
                "disease_name": record.disease_name,
                "confidence_score": record.confidence_score,
                "severity_level": record.severity_level,
                "treatment_recommendation": record.treatment_recommendation,
                "recommendations": recommendations,
                "diagnosis_date": record.diagnosis_date.isoformat() if record.diagnosis_date else None,
                "image_path": record.image_path,
            })

        return history
    except Exception as e:
        logger.warning("Impossible de récupérer l'historique d'analyse", error=str(e), user_id=user_id)
        return []


class PlantDiseaseDiagnostician:
    """Diagnostiqueur maladies plantes via photos"""

    def __init__(self):
        self.model = None
        self.disease_classes = {
            0: {"name": "healthy", "severity": "none", "treatment": "Aucune action requise"},
            1: {"name": "bacterial_blight", "severity": "high", "treatment": "Antibiotiques + Cuivre"},
            2: {"name": "fungal_spot", "severity": "medium", "treatment": "Fongicide systémique"},
            3: {"name": "powdery_mildew", "severity": "medium", "treatment": "Soufre + Ventilation"},
            4: {"name": "rust", "severity": "high", "treatment": "Fongicide triazole"},
            5: {"name": "leaf_blight", "severity": "critical", "treatment": "Éliminer plantes + Fongicide"},
            6: {"name": "mosaic_virus", "severity": "high", "treatment": "Éliminer plantes infectées"},
            7: {"name": "aphid_damage", "severity": "medium", "treatment": "Insecticide systémique"},
            8: {"name": "nutrient_deficiency", "severity": "medium", "treatment": "Analyse sol + Fertilisation"}
        }

        if HAS_CV:
            self.load_disease_model()

    def load_disease_model(self):
        """Charger modèle de diagnostic maladies"""
        try:
            # Utiliser modèle YOLO entraîné pour maladies plantes
            model_path = "models/plant_disease_yolo.pt"
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
            else:
                # Fallback vers modèle général
                self.model = YOLO('yolov8n.pt')
            logger.info("Modèle diagnostic maladies chargé")
        except Exception as e:
            logger.error("Erreur chargement modèle maladies", error=str(e))
            self.model = None

    def diagnose_from_image(self, image_data: bytes, plant_type: str = "unknown",
                           additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Diagnostiquer maladie depuis photo plante

        Args:
            image_data: Données image en bytes
            plant_type: Type de plante (maize, tomato, etc.)
            additional_context: Contexte supplémentaire (localisation, météo, etc.)

        Returns:
            Diagnostic complet avec recommandations
        """
        try:
            # Charger et prétraiter image
            img = Image.open(BytesIO(image_data))
            img = img.convert('RGB')
            img_array = np.array(img)

            # Redimensionner si nécessaire
            if img_array.shape[0] > 1024 or img_array.shape[1] > 1024:
                img = img.resize((640, 640), Image.Resampling.LANCZOS)
                img_array = np.array(img)

            # Diagnostic
            if not HAS_CV or self.model is None:
                return self._fallback_diagnosis(img_array, plant_type, additional_context)

            # Inférence modèle
            results = self.model.predict(img_array, conf=0.25)

            # Analyser résultats
            diagnosis = self._analyze_diagnosis_results(results, plant_type)
            diagnosis.update({
                "plant_type": plant_type,
                "analyzed_at": __import__('datetime').datetime.utcnow().isoformat(),
                "image_quality": self._assess_image_quality(img_array),
                "context_used": additional_context is not None
            })

            # Enrichir avec contexte
            if additional_context:
                diagnosis["contextual_recommendations"] = self._generate_contextual_recommendations(
                    diagnosis, additional_context
                )

            return diagnosis

        except Exception as e:
            logger.error("Erreur diagnostic plante", error=str(e))
            return self._fallback_diagnosis(None, plant_type, additional_context)

    def _analyze_diagnosis_results(self, results, plant_type: str) -> Dict[str, Any]:
        """Analyser résultats du modèle de diagnostic"""
        diseases = []
        max_confidence = 0

        for result in results:
            if result.boxes is None:
                continue

            for box, conf, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                class_id = int(cls)
                if class_id in self.disease_classes:
                    disease_info = self.disease_classes[class_id]
                    diseases.append({
                        "disease": disease_info["name"],
                        "confidence": float(conf),
                        "severity": disease_info["severity"],
                        "bounding_box": [int(x) for x in box],
                        "treatment": disease_info["treatment"]
                    })
                    max_confidence = max(max_confidence, float(conf))

        # Diagnostic principal
        if diseases:
            primary_disease = max(diseases, key=lambda x: x["confidence"])
            overall_severity = primary_disease["severity"]
        else:
            primary_disease = {"disease": "healthy", "confidence": 0.5}
            overall_severity = "none"

        return {
            "primary_disease": primary_disease["disease"],
            "confidence": primary_disease["confidence"],
            "severity": overall_severity,
            "all_detections": diseases,
            "recommendations": self._generate_treatment_plan(diseases, plant_type),
            "prevention_measures": self._get_prevention_measures(primary_disease["disease"]),
            "spread_risk": self._assess_spread_risk(diseases)
        }

    def _generate_treatment_plan(self, diseases: List[Dict], plant_type: str) -> List[Dict[str, Any]]:
        """Générer plan de traitement détaillé"""
        treatments = []

        for disease in diseases:
            if disease["confidence"] > 0.5:
                treatment = {
                    "disease": disease["disease"],
                    "immediate_actions": self._get_immediate_actions(disease["disease"]),
                    "chemical_treatment": disease["treatment"],
                    "organic_alternatives": self._get_organic_alternatives(disease["disease"]),
                    "timeline": self._get_treatment_timeline(disease["severity"]),
                    "follow_up": "Surveiller évolution 7 jours après traitement"
                }
                treatments.append(treatment)

        if not treatments:
            treatments.append({
                "disease": "healthy",
                "immediate_actions": ["Continuer bonnes pratiques"],
                "chemical_treatment": "Aucun",
                "organic_alternatives": ["Compostage", "Rotation culturale"],
                "timeline": "Maintenance préventive",
                "follow_up": "Contrôle régulier"
            })

        return treatments

    def _get_immediate_actions(self, disease: str) -> List[str]:
        """Actions immédiates selon maladie"""
        actions = {
            "bacterial_blight": ["Isoler plante malade", "Désinfecter outils", "Améliorer drainage"],
            "fungal_spot": ["Retirer feuilles infectées", "Améliorer circulation air", "Réduire arrosage"],
            "powdery_mildew": ["Augmenter ventilation", "Réduire humidité", "Éviter arrosage feuilles"],
            "rust": ["Retirer parties infectées", "Améliorer espacement", "Fongicide préventif"],
            "leaf_blight": ["Éliminer plante", "Désinfecter sol", "Pas de plantation même famille"],
            "mosaic_virus": ["Détruire plante", "Contrôler pucerons", "Utiliser semences certifiées"],
            "aphid_damage": ["Lavage à l'eau", "Introduire auxiliaires", "Huile insecticide"],
            "nutrient_deficiency": ["Analyse foliaire", "Amendement sol", "pH correction"]
        }
        return actions.get(disease, ["Consulter spécialiste agricole"])

    def _get_organic_alternatives(self, disease: str) -> List[str]:
        """Alternatives biologiques aux traitements chimiques"""
        alternatives = {
            "bacterial_blight": ["Bicarbonate soude", "Huile neem", "Purins d'ortie"],
            "fungal_spot": ["Soufre", "Bicarbonate", "Extrait d'ail"],
            "powdery_mildew": ["Bicarbonate potassique", "Lait écrémé", "Savon noir"],
            "rust": ["Soufre micronisé", "Huile essentielle tea tree", "Propolis"],
            "aphid_damage": ["Savon noir", "Huile de colza", "Pucerons auxiliaires"],
            "nutrient_deficiency": ["Compost", "Engrais verts", "Thé de compost"]
        }
        return alternatives.get(disease, ["Méthodes culturales", "Prévention"])

    def _get_treatment_timeline(self, severity: str) -> str:
        """Timeline traitement selon sévérité"""
        timelines = {
            "critical": "Action immédiate - 24-48h",
            "high": "Traitement dans la semaine",
            "medium": "Traitement dès que possible",
            "low": "Surveillance et traitement préventif",
            "none": "Maintenance préventive"
        }
        return timelines.get(severity, "Consulter spécialiste")

    def _get_prevention_measures(self, disease: str) -> List[str]:
        """Mesures préventives selon maladie"""
        preventions = {
            "bacterial_blight": ["Rotation culturale 3 ans", "Semences saines", "Éviter excès eau"],
            "fungal_spot": ["Espacement plantes", "Éviter arrosage feuilles", "Paillage"],
            "powdery_mildew": ["Bonne circulation air", "Éviter stress hydrique", "Semences résistantes"],
            "rust": ["Semences résistantes", "Éviter humidité", "Surveillance régulière"],
            "mosaic_virus": ["Contrôle pucerons", "Semences certifiées", "Élimination adventices"],
            "aphid_damage": ["Introduire auxiliaires", "Semences saines", "Rotation culturale"],
            "nutrient_deficiency": ["Analyse sol régulière", "Fertilisation équilibrée", "pH optimal"]
        }
        return preventions.get(disease, ["Bonnes pratiques agricoles", "Surveillance régulière"])

    def _assess_spread_risk(self, diseases: List[Dict]) -> str:
        """Évaluer risque de propagation"""
        if not diseases:
            return "none"

        high_risk_diseases = ["mosaic_virus", "leaf_blight", "bacterial_blight"]
        medium_risk_diseases = ["rust", "powdery_mildew", "aphid_damage"]

        detected_names = [d["disease"] for d in diseases]

        if any(d in high_risk_diseases for d in detected_names):
            return "high"
        elif any(d in medium_risk_diseases for d in detected_names):
            return "medium"
        else:
            return "low"

    def _assess_image_quality(self, img_array: np.ndarray) -> str:
        """Évaluer qualité de l'image pour diagnostic"""
        try:
            # Vérifier luminosité
            gray = np.dot(img_array[...,:3], [0.299, 0.587, 0.114])
            brightness = np.mean(gray)

            if brightness < 50:
                return "too_dark"
            elif brightness > 200:
                return "too_bright"
            else:
                # Vérifier netteté (variance du Laplacien)
                laplacian_var = np.var(cv2.Laplacian(gray, cv2.CV_64F)) if 'cv2' in globals() else 100
                if laplacian_var < 50:
                    return "blurry"
                else:
                    return "good"
        except:
            return "unknown"

    def _generate_contextual_recommendations(self, diagnosis: Dict, context: Dict) -> List[str]:
        """Générer recommandations basées sur contexte"""
        recommendations = []

        # Contexte météo
        weather = context.get("weather", {})
        temp = weather.get("temperature", 25)
        humidity = weather.get("humidity", 60)

        if diagnosis["severity"] in ["high", "critical"]:
            if humidity > 80:
                recommendations.append("Humidité élevée favorise développement - améliorer ventilation")
            if temp > 30:
                recommendations.append("Chaleur favorise stress - irrigation supplémentaire")

        # Contexte localisation
        location = context.get("location", {})
        if location.get("region") in ["Tombouctou", "Gao"]:
            recommendations.append("Région sahélienne - surveiller particulièrement sécheresse")

        return recommendations

    def _fallback_diagnosis(self, img_array, plant_type: str, context: Dict = None) -> Dict[str, Any]:
        """Diagnostic fallback quand modèle indisponible"""
        logger.warning("Mode fallback diagnostic plantes activé")

        return {
            "primary_disease": "unknown",
            "confidence": 0.0,
            "severity": "unknown",
            "all_detections": [],
            "recommendations": [{
                "disease": "unknown",
                "immediate_actions": ["Consulter spécialiste agricole"],
                "chemical_treatment": "À déterminer",
                "organic_alternatives": ["Méthodes préventives"],
                "timeline": "Urgent",
                "follow_up": "Diagnostic professionnel requis"
            }],
            "prevention_measures": ["Bonnes pratiques culturales", "Surveillance régulière"],
            "spread_risk": "unknown",
            "plant_type": plant_type,
            "analyzed_at": __import__('datetime').datetime.utcnow().isoformat(),
            "image_quality": "unknown",
            "context_used": False,
            "fallback_mode": True
        }


# Instance globale du diagnostiqueur
plant_diagnostician = PlantDiseaseDiagnostician()


def diagnose_plant_disease(image_data: bytes, plant_type: str = "unknown",
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fonction principale pour diagnostic maladie plante
    Utilisée par les routes API
    """
    return plant_diagnostician.diagnose_from_image(image_data, plant_type, context)