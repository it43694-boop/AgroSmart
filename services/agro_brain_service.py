# ==========================================
# AGRO-BRAIN SERVICE - IA Contextuelle Africaine
# Intelligence Artificielle Révolutionnaire pour l'Agriculture
# ==========================================

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

# ML Libraries (optionnel)
try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, mean_squared_error

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    RandomForestClassifier = RandomForestRegressor = StandardScaler = None
    LabelEncoder = train_test_split = accuracy_score = mean_squared_error = None

# Redis pour cache haute performance
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class MultilingualChatbot:
    """Chatbot multilingue simple avec fallback local."""

    def __init__(self):
        self.supported_languages = {"fr", "en", "bm"}

    def chat(self, message: str, language: str = "fr") -> Dict[str, Any]:
        lang = (language or "fr").lower()
        if lang not in self.supported_languages:
            lang = "fr"

        text = message.strip() or "Bonjour"
        intent = "general"
        if any(keyword in text.lower() for keyword in ["risque", "risk", "sécheresse", "drought"]):
            intent = "risk"
        elif any(keyword in text.lower() for keyword in ["recommand", "recommend", "culture", "crop"]):
            intent = "recommendation"

        return {
            "text": f"[fallback] Réponse {lang.upper()} : {text}",
            "language": lang,
            "intent": intent,
            "entities": {},
        }


class ReportGenerator:
    """Générateur de rapports markdown simple."""

    def generate_weekly_report(self, region: str, crop_types: List[str], user_name: str) -> str:
        crops = ", ".join(crop_types or ["cultures diverses"])
        return (
            f"# Rapport hebdomadaire\n"
            f"- Région : {region}\n"
            f"- Utilisateur : {user_name}\n"
            f"- Cultures suivies : {crops}\n"
            f"- Statut : surveillance active"
        )

    def generate_monthly_report(self, region: str, crop_types: List[str], user_name: str) -> str:
        crops = ", ".join(crop_types or ["cultures diverses"])
        return (
            f"# Rapport mensuel\n"
            f"- Région : {region}\n"
            f"- Utilisateur : {user_name}\n"
            f"- Cultures suivies : {crops}\n"
            f"- Statut : synthèse mensuelle prête"
        )

    def generate_disease_alert(self, disease_name: str, crop_type: str, severity: str) -> str:
        return (
            f"# Alerte maladie\n"
            f"- Maladie : {disease_name}\n"
            f"- Culture : {crop_type}\n"
            f"- Sévérité : {severity}\n"
            f"- Action : renforcer la surveillance et consulter l'expert local"
        )


# ==========================================
# DONNÉES CONTEXTUELLES AFRICAINES
# ==========================================

@dataclass
class MaliSoilData:
    """Données pédologiques du Mali par région"""
    region: str
    soil_type: str  # sableux, argileux, limoneux
    ph_level: float
    organic_matter: float
    drainage: str  # bon, moyen, mauvais
    fertility_index: float  # 0-100

@dataclass
class MaliClimateData:
    """Données climatiques du Mali par région et saison"""
    region: str
    season: str  # hivernage, sèche
    avg_temp: float
    rainfall_mm: float
    humidity_percent: float
    drought_risk: str  # faible, moyen, élevé

@dataclass
class CropRecommendation:
    """Recommandation de culture optimisée"""
    crop_name: str
    confidence_score: float
    expected_yield: float  # tonnes/ha
    water_requirement: float  # mm
    fertilizer_needs: Dict[str, float]
    risk_factors: List[str]
    adaptation_tips: List[str]

class RiskLevel(Enum):
    LOW = "faible"
    MEDIUM = "moyen"
    HIGH = "élevé"
    CRITICAL = "critique"

# ==========================================
# BASE DE CONNAISSANCES MALIENNE
# ==========================================

MALI_SOIL_DATA = {
    "Bamako": MaliSoilData("Bamako", "sableux", 6.2, 1.8, "moyen", 65.0),
    "Sikasso": MaliSoilData("Sikasso", "argileux", 5.8, 2.1, "bon", 78.0),
    "Mopti": MaliSoilData("Mopti", "limoneux", 6.5, 1.5, "mauvais", 55.0),
    "Tombouctou": MaliSoilData("Tombouctou", "sableux", 7.1, 0.8, "mauvais", 35.0),
    "Kayes": MaliSoilData("Kayes", "sableux", 5.9, 1.2, "bon", 58.0),
    "Koulikoro": MaliSoilData("Koulikoro", "argileux", 6.0, 2.0, "moyen", 72.0),
    "Ségou": MaliSoilData("Ségou", "limoneux", 6.3, 1.7, "bon", 68.0),
    "Gao": MaliSoilData("Gao", "sableux", 7.0, 0.9, "mauvais", 42.0),
}

MALI_CLIMATE_DATA = {
    "hivernage": {
        "sud": MaliClimateData("sud", "hivernage", 28.0, 1200.0, 75.0, "faible"),
        "centre": MaliClimateData("centre", "hivernage", 30.0, 800.0, 65.0, "moyen"),
        "nord": MaliClimateData("nord", "hivernage", 35.0, 200.0, 45.0, "élevé"),
    },
    "sèche": {
        "sud": MaliClimateData("sud", "sèche", 32.0, 50.0, 55.0, "moyen"),
        "centre": MaliClimateData("centre", "sèche", 38.0, 20.0, 35.0, "élevé"),
        "nord": MaliClimateData("nord", "sèche", 42.0, 5.0, 25.0, "critique"),
    }
}

# Cultures traditionnelles maliennes avec leurs caractéristiques
MALI_CROPS = {
    "mil": {
        "cycle_days": 90,
        "water_need": 300,
        "optimal_ph": [5.5, 7.0],
        "soil_types": ["sableux", "limoneux"],
        "regions": ["Sikasso", "Ségou", "Mopti"],
        "yield_avg": 1.2,  # tonnes/ha
        "fertilizer": {"azote": 40, "phosphore": 20, "potassium": 10}
    },
    "maïs": {
        "cycle_days": 120,
        "water_need": 500,
        "optimal_ph": [5.8, 7.2],
        "soil_types": ["argileux", "limoneux"],
        "regions": ["Bamako", "Koulikoro", "Sikasso"],
        "yield_avg": 3.5,
        "fertilizer": {"azote": 80, "phosphore": 40, "potassium": 30}
    },
    "riz": {
        "cycle_days": 150,
        "water_need": 1200,
        "optimal_ph": [6.0, 7.5],
        "soil_types": ["argileux"],
        "regions": ["Ségou", "Koulikoro"],
        "yield_avg": 4.2,
        "fertilizer": {"azote": 100, "phosphore": 50, "potassium": 40}
    },
    "arachide": {
        "cycle_days": 100,
        "water_need": 400,
        "optimal_ph": [5.5, 6.5],
        "soil_types": ["sableux", "limoneux"],
        "regions": ["Kayes", "Koulikoro", "Sikasso"],
        "yield_avg": 1.8,
        "fertilizer": {"azote": 20, "phosphore": 30, "potassium": 15}
    },
    "coton": {
        "cycle_days": 180,
        "water_need": 700,
        "optimal_ph": [6.0, 7.0],
        "soil_types": ["argileux", "limoneux"],
        "regions": ["Sikasso", "Ségou"],
        "yield_avg": 2.1,
        "fertilizer": {"azote": 60, "phosphore": 35, "potassium": 25}
    }
}

# ==========================================
# AGRO-BRAIN SERVICE PRINCIPAL
# ==========================================

class AgroBrainService:
    """
    Service IA Révolutionnaire pour l'Agriculture Africaine

    Capacités :
    - Recommandations de cultures contextuelles
    - Prédictions de rendement optimisées
    - Alertes de risque intelligentes
    - Optimisation des ressources
    """

    def __init__(self):
        self.redis_client = None
        self.models = {}
        self.scalers = {}
        self.encoders = {}

        # Redis seulement si explicitement configure (evite erreur localhost par defaut)
        redis_url = os.getenv("REDIS_URL", "").strip()
        redis_host = os.getenv("REDIS_HOST", "").strip()
        if REDIS_AVAILABLE and (redis_url or redis_host):
            try:
                if redis_url:
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                else:
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=int(os.getenv("REDIS_PORT", 6379)),
                        db=int(os.getenv("REDIS_DB", 0)),
                        decode_responses=True,
                    )
                self.redis_client.ping()
                logger.info("Redis connecte pour AgroBrain")
            except Exception as e:
                logger.info("Redis AgroBrain indisponible, cache desactive: %s", e)
                self.redis_client = None

        # Charger les modèles entraînés
        self._load_models()

    def _load_models(self):
        """Charge les modèles ML pré-entraînés"""
        try:
            # Modèle de recommandation de cultures
            model_path = "models/crop_recommendation_model.pkl"
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.models['crop_recommendation'] = pickle.load(f)
                logger.info("Modèle de recommandation de cultures chargé")

            # Modèle de prédiction de rendement
            model_path = "models/yield_prediction_model.pkl"
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.models['yield_prediction'] = pickle.load(f)
                logger.info("Modèle de prédiction de rendement chargé")

            # Scalers et encoders
            scaler_path = "models/feature_scaler.pkl"
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scalers['features'] = pickle.load(f)

            encoder_path = "models/crop_encoder.pkl"
            if os.path.exists(encoder_path):
                with open(encoder_path, 'rb') as f:
                    self.encoders['crops'] = pickle.load(f)

        except Exception as e:
            logger.warning(f"Impossible de charger les modèles: {e}")
            # Utiliser des modèles de fallback simples
            self._create_fallback_models()

    def _create_fallback_models(self):
        """Crée des modèles de fallback simples si les modèles entraînés ne sont pas disponibles"""
        logger.info("Création de modèles de fallback")

        # Modèle simple de recommandation basé sur les données maliennes
        self.models['crop_recommendation'] = self._create_simple_crop_model()
        self.models['yield_prediction'] = self._create_simple_yield_model()

    def _create_simple_crop_model(self):
        """Modèle simple de recommandation de cultures basé sur les données maliennes"""
        # Logique basée sur les données MALI_CROPS
        return lambda region, soil_type, season: self._recommend_crop_simple(region, soil_type, season)

    def _create_simple_yield_model(self):
        """Modèle simple de prédiction de rendement"""
        return lambda crop, region, rainfall, fertilizer: self._predict_yield_simple(crop, region, rainfall, fertilizer)

    def _recommend_crop_simple(self, region: str, soil_type: str, season: str) -> CropRecommendation:
        """Recommandation simple basée sur les données maliennes"""

        # Trouver les cultures adaptées à la région et au sol
        suitable_crops = []
        for crop_name, crop_data in MALI_CROPS.items():
            if region in crop_data["regions"] and soil_type in crop_data["soil_types"]:
                suitable_crops.append((crop_name, crop_data))

        if not suitable_crops:
            # Fallback vers le mil (culture de base malienne)
            crop_name, crop_data = "mil", MALI_CROPS["mil"]
        else:
            # Sélectionner la culture avec le meilleur rendement
            crop_name, crop_data = max(suitable_crops, key=lambda x: x[1]["yield_avg"])

        # Calculer le score de confiance basé sur l'adaptation
        confidence = 0.8 if region in crop_data["regions"] else 0.6

        # Ajuster selon la saison
        if season == "sèche":
            expected_yield = crop_data["yield_avg"] * 0.7  # Réduction en saison sèche
            risk_factors = ["Saison sèche - irrigation nécessaire"]
        else:
            expected_yield = crop_data["yield_avg"]
            risk_factors = []

        # Conseils d'adaptation
        adaptation_tips = [
            f"Utiliser {crop_data['fertilizer']['azote']}kg/ha d'azote",
            f"pH optimal: {crop_data['optimal_ph'][0]}-{crop_data['optimal_ph'][1]}",
            f"Besoin en eau: {crop_data['water_need']}mm par cycle"
        ]

        return CropRecommendation(
            crop_name=crop_name,
            confidence_score=confidence,
            expected_yield=expected_yield,
            water_requirement=crop_data["water_need"],
            fertilizer_needs=crop_data["fertilizer"],
            risk_factors=risk_factors,
            adaptation_tips=adaptation_tips
        )

    def _predict_yield_simple(self, crop: str, region: str, rainfall: float, fertilizer: float) -> float:
        """Prédiction simple de rendement"""
        if crop not in MALI_CROPS:
            return 1.0  # Valeur par défaut

        base_yield = MALI_CROPS[crop]["yield_avg"]

        # Facteurs multiplicatifs
        rainfall_factor = min(1.5, max(0.3, rainfall / MALI_CROPS[crop]["water_need"]))
        fertilizer_factor = min(1.4, max(0.6, fertilizer / 100))  # Supposant 100kg/ha comme référence

        # Facteur régional (certaines régions sont plus productives)
        region_factors = {
            "Sikasso": 1.2, "Ségou": 1.1, "Koulikoro": 1.1,
            "Bamako": 1.0, "Mopti": 0.9, "Kayes": 0.8,
            "Tombouctou": 0.6, "Gao": 0.7
        }
        region_factor = region_factors.get(region, 1.0)

        return base_yield * rainfall_factor * fertilizer_factor * region_factor

    def _get_cache_key(self, operation: str, params: Dict) -> str:
        """Génère une clé de cache unique"""
        param_str = json.dumps(params, sort_keys=True)
        return f"agrobrain:{operation}:{hash(param_str)}"

    def _get_cached_result(self, key: str) -> Optional[Any]:
        """Récupère un résultat en cache"""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Erreur cache: {e}")

        return None

    def _cache_result(self, key: str, result: Any, ttl: int = 3600):
        """Met en cache un résultat"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(key, ttl, json.dumps(result))
        except Exception as e:
            logger.warning(f"Erreur mise en cache: {e}")

    def recommend_crop(self, region: str, soil_type: str, season: str,
                      temperature: float = None, rainfall: float = None) -> CropRecommendation:
        """
        Recommande la meilleure culture pour une situation donnée

        Args:
            region: Région du Mali (ex: "Sikasso")
            soil_type: Type de sol ("sableux", "argileux", "limoneux")
            season: Saison ("hivernage", "sèche")
            temperature: Température actuelle (°C)
            rainfall: Pluviométrie récente (mm)

        Returns:
            CropRecommendation: Recommandation optimisée
        """

        # Vérifier le cache
        cache_key = self._get_cache_key("recommend_crop", {
            "region": region, "soil_type": soil_type, "season": season,
            "temperature": temperature, "rainfall": rainfall
        })

        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.info(f"Recommandation récupérée du cache pour {region}")
            return CropRecommendation(**cached_result)

        # Utiliser le modèle de recommandation
        if 'crop_recommendation' in self.models:
            # Utiliser le modèle ML avancé
            recommendation = self._advanced_crop_recommendation(
                region, soil_type, season, temperature, rainfall
            )
        else:
            # Utiliser le modèle simple
            recommendation = self._recommend_crop_simple(region, soil_type, season)

        # Ajuster selon les conditions météo actuelles
        if temperature is not None and rainfall is not None:
            recommendation = self._adjust_for_weather(recommendation, temperature, rainfall)

        # Mettre en cache
        self._cache_result(cache_key, recommendation.__dict__)

        logger.info(f"Recommandation générée pour {region}: {recommendation.crop_name} (confiance: {recommendation.confidence_score:.2f})")

        return recommendation

    def _advanced_crop_recommendation(self, region: str, soil_type: str, season: str,
                                    temperature: float, rainfall: float) -> CropRecommendation:
        """Recommandation avancée utilisant les modèles ML"""
        # Préparer les features
        features = self._prepare_crop_features(region, soil_type, season, temperature, rainfall)

        # Prédire avec le modèle
        model = self.models['crop_recommendation']
        scaler = self.scalers.get('features')

        if scaler:
            features_scaled = scaler.transform([features])
        else:
            features_scaled = [features]

        # Prédiction (à adapter selon le modèle réel)
        # Pour l'exemple, on utilise toujours la logique simple
        return self._recommend_crop_simple(region, soil_type, season)

    def _prepare_crop_features(self, region: str, soil_type: str, season: str,
                             temperature: float, rainfall: float) -> List[float]:
        """Prépare les features pour le modèle ML"""
        # Encoder les variables catégorielles
        region_encoded = hash(region) % 1000  # Simple encoding
        soil_encoded = {"sableux": 0, "argileux": 1, "limoneux": 2}.get(soil_type, 0)
        season_encoded = 1 if season == "hivernage" else 0

        return [
            region_encoded,
            soil_encoded,
            season_encoded,
            temperature or 25.0,
            rainfall or 500.0
        ]

    def _adjust_for_weather(self, recommendation: CropRecommendation,
                          temperature: float, rainfall: float) -> CropRecommendation:
        """Ajuste la recommandation selon les conditions météo actuelles"""

        # Ajuster le rendement selon la pluie
        if rainfall < 200:  # Sécheresse
            recommendation.expected_yield *= 0.6
            recommendation.risk_factors.append("Risque de sécheresse détecté")
            recommendation.adaptation_tips.append("Augmenter l'irrigation de 30%")

        elif rainfall > 1500:  # Pluies excessives
            recommendation.expected_yield *= 0.8
            recommendation.risk_factors.append("Risques d'inondation")
            recommendation.adaptation_tips.append("Améliorer le drainage")

        # Ajuster selon la température
        if temperature > 35:
            recommendation.expected_yield *= 0.7
            recommendation.risk_factors.append("Température élevée")
            recommendation.adaptation_tips.append("Ombrage nécessaire")

        return recommendation

    def predict_yield(self, crop: str, region: str, soil_type: str,
                     rainfall: float, fertilizer_amount: float,
                     temperature: float = None) -> Dict[str, Any]:
        """
        Prédit le rendement d'une culture donnée

        Args:
            crop: Nom de la culture
            region: Région du Mali
            soil_type: Type de sol
            rainfall: Pluviométrie (mm)
            fertilizer_amount: Quantité d'engrais (kg/ha)
            temperature: Température (°C)

        Returns:
            Dict avec prédiction et intervalles de confiance
        """

        # Vérifier le cache
        cache_key = self._get_cache_key("predict_yield", {
            "crop": crop, "region": region, "soil_type": soil_type,
            "rainfall": rainfall, "fertilizer": fertilizer_amount, "temperature": temperature
        })

        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        # Utiliser le modèle de prédiction
        if 'yield_prediction' in self.models:
            prediction = self._advanced_yield_prediction(
                crop, region, soil_type, rainfall, fertilizer_amount, temperature
            )
        else:
            predicted_yield = self._predict_yield_simple(crop, region, rainfall, fertilizer_amount)
            prediction = {
                "predicted_yield": predicted_yield,
                "confidence_interval": [predicted_yield * 0.8, predicted_yield * 1.2],
                "risk_level": self._calculate_risk_level(crop, region, rainfall, fertilizer_amount),
                "optimization_tips": self._generate_optimization_tips(crop, predicted_yield)
            }

        # Mettre en cache
        self._cache_result(cache_key, prediction)

        return prediction

    def _advanced_yield_prediction(self, crop: str, region: str, soil_type: str,
                                 rainfall: float, fertilizer_amount: float,
                                 temperature: float) -> Dict[str, Any]:
        """Prédiction avancée utilisant les modèles ML"""
        # Pour l'exemple, utiliser la prédiction simple
        predicted_yield = self._predict_yield_simple(crop, region, rainfall, fertilizer_amount)

        return {
            "predicted_yield": predicted_yield,
            "confidence_interval": [predicted_yield * 0.85, predicted_yield * 1.15],
            "risk_level": self._calculate_risk_level(crop, region, rainfall, fertilizer_amount),
            "optimization_tips": self._generate_optimization_tips(crop, predicted_yield)
        }

    def _calculate_risk_level(self, crop: str, region: str, rainfall: float, fertilizer: float) -> str:
        """Calcule le niveau de risque de la prédiction"""

        if crop not in MALI_CROPS:
            return RiskLevel.HIGH.value

        crop_data = MALI_CROPS[crop]
        risk_score = 0

        # Risque lié à la pluie
        rainfall_ratio = rainfall / crop_data["water_need"]
        if rainfall_ratio < 0.5:
            risk_score += 3  # Très sec
        elif rainfall_ratio < 0.8:
            risk_score += 1  # Sec

        # Risque lié aux engrais
        fertilizer_ratio = fertilizer / 100  # Supposant 100kg/ha optimal
        if fertilizer_ratio < 0.5:
            risk_score += 2  # Sous-fertilisé
        elif fertilizer_ratio > 1.5:
            risk_score += 1  # Sur-fertilisé

        # Risque régional
        region_risks = {
            "Tombouctou": 2, "Gao": 2, "Mopti": 1,
            "Kayes": 1, "Sikasso": 0, "Bamako": 0
        }
        risk_score += region_risks.get(region, 0)

        # Déterminer le niveau
        if risk_score >= 4:
            return RiskLevel.CRITICAL.value
        elif risk_score >= 2:
            return RiskLevel.HIGH.value
        elif risk_score >= 1:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value

    def _generate_optimization_tips(self, crop: str, predicted_yield: float) -> List[str]:
        """Génère des conseils d'optimisation"""

        if crop not in MALI_CROPS:
            return ["Consultez un agronome local"]

        crop_data = MALI_CROPS[crop]
        tips = []

        # Conseil sur l'irrigation
        tips.append(f"Maintenir {crop_data['water_need']}mm d'eau par cycle")

        # Conseil sur les engrais
        fertilizer = crop_data['fertilizer']
        tips.append(f"Utiliser {fertilizer['azote']}kg/ha N, {fertilizer['phosphore']}kg/ha P, {fertilizer['potassium']}kg/ha K")

        # Conseil sur le rendement attendu
        tips.append(f"Rendement attendu: {predicted_yield:.1f} tonnes/ha")

        return tips

    def detect_risks(self, region: str, crop: str, current_conditions: Dict) -> List[Dict[str, Any]]:
        """
        Détecte les risques agricoles en temps réel

        Args:
            region: Région concernée
            crop: Culture concernée
            current_conditions: Conditions actuelles (température, humidité, etc.)

        Returns:
            Liste des risques détectés
        """

        risks = []

        # Analyser les conditions météo
        temperature = current_conditions.get('temperature', 25)
        humidity = current_conditions.get('humidity', 50)
        rainfall = current_conditions.get('rainfall', 0)

        # Risque de chaleur excessive
        if temperature > 35:
            risks.append({
                "type": "heat_stress",
                "level": RiskLevel.HIGH.value,
                "description": f"Température élevée détectée ({temperature}°C)",
                "recommendations": ["Installer un ombrage", "Augmenter l'irrigation", "Surveiller les signes de stress"]
            })

        # Risque de sécheresse
        if rainfall < 10 and humidity < 30:  # Pas de pluie récente et air sec
            risks.append({
                "type": "drought",
                "level": RiskLevel.CRITICAL.value,
                "description": "Risque de sécheresse imminent",
                "recommendations": ["Irrigation d'urgence", "Utiliser des variétés résistantes", "Contacter l'assistance"]
            })

        # Risque de maladie (basé sur conditions favorables)
        if humidity > 80 and temperature > 25:
            risks.append({
                "type": "disease",
                "level": RiskLevel.MEDIUM.value,
                "description": "Conditions favorables aux maladies",
                "recommendations": ["Appliquer un traitement préventif", "Améliorer la ventilation", "Surveiller les symptômes"]
            })

        return risks

    def optimize_resources(self, farm_data: Dict) -> Dict[str, Any]:
        """
        Optimise l'utilisation des ressources pour une exploitation

        Args:
            farm_data: Données de l'exploitation (cultures, surface, ressources disponibles)

        Returns:
            Plan d'optimisation des ressources
        """

        crops = farm_data.get('crops', [])
        total_area = farm_data.get('total_area', 0)
        water_available = farm_data.get('water_available', 0)
        budget = farm_data.get('budget', 0)

        optimization = {
            "water_allocation": {},
            "fertilizer_plan": {},
            "expected_revenue": 0,
            "resource_efficiency": 0,
            "recommendations": []
        }

        total_water_needed = 0
        total_cost = 0

        for crop in crops:
            crop_name = crop['name']
            area = crop['area']

            if crop_name in MALI_CROPS:
                crop_data = MALI_CROPS[crop_name]

                # Calcul des besoins en eau
                water_needed = (crop_data['water_need'] * area) / 1000  # m³
                total_water_needed += water_needed

                # Calcul des coûts d'engrais
                fertilizer = crop_data['fertilizer']
                fertilizer_cost = (
                    fertilizer['azote'] * 2.5 +  # Prix au kg
                    fertilizer['phosphore'] * 3.0 +
                    fertilizer['potassium'] * 2.0
                ) * area
                total_cost += fertilizer_cost

                # Revenu attendu
                expected_yield = crop_data['yield_avg'] * area
                revenue = expected_yield * 150  # Prix moyen du mil au Mali (150 000 F CFA/tonne)
                optimization["expected_revenue"] += revenue

                optimization["water_allocation"][crop_name] = water_needed
                optimization["fertilizer_plan"][crop_name] = fertilizer

        # Calculer l'efficacité des ressources
        if total_water_needed > 0:
            optimization["resource_efficiency"] = min(1.0, water_available / total_water_needed)

        # Générer des recommandations
        if total_cost > budget:
            optimization["recommendations"].append(f"Budget dépassé de {total_cost - budget:.0f} F CFA - réduire les surfaces")

        if total_water_needed > water_available:
            optimization["recommendations"].append(f"Eau insuffisante - déficit de {total_water_needed - water_available:.1f} m³")

        if optimization["resource_efficiency"] < 0.8:
            optimization["recommendations"].append("Eau limitée - envisager des cultures moins exigeantes")

        return optimization

    def _aggregate_risk_score(self, risks: List[Dict[str, Any]]) -> float:
        score = 0.0
        weights = {
            RiskLevel.LOW.value: 1.0,
            RiskLevel.MEDIUM.value: 2.5,
            RiskLevel.HIGH.value: 4.0,
            RiskLevel.CRITICAL.value: 5.0,
        }
        for risk in risks:
            score += weights.get(risk.get("level"), 1.0)
        return float(score)

    def simulate_scenario(self, crop: str, region: str, soil_type: str,
                          baseline_rainfall: float, baseline_fertilizer: float,
                          baseline_temperature: Optional[float] = None,
                          irrigation_change_pct: float = 0.0,
                          fertilizer_change_pct: float = 0.0) -> Dict[str, Any]:
        """
        Simule un scénario "Que se passe-t-il si..." pour une culture donnée.
        """
        # Valeurs de base
        baseline_temperature = baseline_temperature if baseline_temperature is not None else 28.0
        baseline_conditions = {
            "temperature": baseline_temperature,
            "humidity": 55.0,
            "rainfall": baseline_rainfall,
        }

        projected_rainfall = max(0.0, baseline_rainfall * (1 + irrigation_change_pct / 100.0))
        projected_fertilizer = max(0.0, baseline_fertilizer * (1 + fertilizer_change_pct / 100.0))
        projected_conditions = {
            "temperature": baseline_temperature,
            "humidity": 55.0,
            "rainfall": projected_rainfall,
        }

        baseline_prediction = self.predict_yield(crop, region, soil_type, baseline_rainfall, baseline_fertilizer, baseline_temperature)
        projected_prediction = self.predict_yield(crop, region, soil_type, projected_rainfall, projected_fertilizer, baseline_temperature)

        baseline_risks = self.detect_risks(region, crop, baseline_conditions)
        projected_risks = self.detect_risks(region, crop, projected_conditions)

        baseline_cost = round(baseline_fertilizer * 2.5 + baseline_rainfall * 0.12, 2)
        projected_cost = round(projected_fertilizer * 2.5 + projected_rainfall * 0.12, 2)

        baseline_score = self._aggregate_risk_score(baseline_risks)
        projected_score = self._aggregate_risk_score(projected_risks)

        delta_yield = round(projected_prediction["predicted_yield"] - baseline_prediction["predicted_yield"], 2)
        delta_cost = round(projected_cost - baseline_cost, 2)
        delta_risk_score = round(projected_score - baseline_score, 2)

        summary = (
            f"Simulation '{crop}' dans {region} : rendement prévu "
            f"de {baseline_prediction['predicted_yield']:.2f}→{projected_prediction['predicted_yield']:.2f} t/ha, "
            f"coût {baseline_cost:.2f}→{projected_cost:.2f}, "
            f"risque {baseline_score:.1f}→{projected_score:.1f}."
        )

        return {
            "crop": crop,
            "region": region,
            "soil_type": soil_type,
            "baseline": {
                "predicted_yield": baseline_prediction["predicted_yield"],
                "cost_estimate": baseline_cost,
                "risk_score": baseline_score,
                "risks": baseline_risks,
            },
            "projected": {
                "predicted_yield": projected_prediction["predicted_yield"],
                "cost_estimate": projected_cost,
                "risk_score": projected_score,
                "risks": projected_risks,
            },
            "delta_yield": delta_yield,
            "delta_cost": delta_cost,
            "delta_risk_score": delta_risk_score,
            "summary": summary,
            "details": {
                "baseline_rainfall": baseline_rainfall,
                "baseline_fertilizer": baseline_fertilizer,
                "irrigation_change_pct": irrigation_change_pct,
                "fertilizer_change_pct": fertilizer_change_pct,
                "projected_rainfall": projected_rainfall,
                "projected_fertilizer": projected_fertilizer,
            }
        }

    def _get_region_from_coords(self, lat: float, lon: float) -> str:
        """Détermine la région du Mali à partir des coordonnées"""
        # Mapping simple des régions du Mali
        if 10 <= lat <= 14 and -12 <= lon <= -7:
            return "Sikasso"  # Sud agricole
        elif 12 <= lat <= 16 and -9 <= lon <= -4:
            return "Ségou"  # Centre
        elif 11 <= lat <= 15 and -10 <= lon <= -6:
            return "Koulikoro"  # Ouest
        else:
            return "Bamako"  # Par défaut

    def _get_soil_type_from_region(self, region: str) -> str:
        """Détermine le type de sol principal d'une région"""
        soil_mapping = {
            "Sikasso": "sableux",
            "Ségou": "argileux",
            "Koulikoro": "limoneux",
            "Bamako": "sableux"
        }
        return soil_mapping.get(region, "sableux")

    def _get_current_season(self) -> str:
        """Détermine la saison actuelle au Mali"""
        from datetime import datetime
        month = datetime.now().month
        # Saison des pluies: juin-octobre (hivernage)
        # Saison sèche: novembre-mai
        return "hivernage" if 6 <= month <= 10 else "sèche"

    def get_recommendations(self, user, lat: float = 0.0, lon: float = 0.0) -> Dict[str, Any]:
        """
        Génère un ensemble complet de recommandations IA pour l'utilisateur

        Args:
            user: Objet utilisateur avec ses données agricoles
            lat: Latitude de la localisation
            lon: Longitude de la localisation

        Returns:
            Dict contenant toutes les recommandations IA
        """
        try:
            # Déterminer la région et le type de sol
            region = self._get_region_from_coords(lat, lon)
            soil_type = self._get_soil_type_from_region(region)
            season = self._get_current_season()

            # Recommandation de culture
            crop_rec = self.recommend_crop(region, soil_type, season)

            # Prédiction de rendement pour la culture recommandée
            yield_pred = self.predict_yield(
                crop_rec.crop_name, region, soil_type,
                rainfall=600,  # Valeur par défaut pour l'hivernage
                fertilizer_amount=100,  # kg/ha
                temperature=28  # °C moyenne
            )

            # Détection de risques
            current_conditions = {
                "temperature": 28,
                "humidity": 60,
                "rainfall": 600,
                "soil_moisture": 0.6
            }
            risks = self.detect_risks(region, crop_rec.crop_name, current_conditions)

            # Optimisation des ressources
            crops_data = []
            for crop in (user.crops or []):
                if isinstance(crop, dict):
                    crops_data.append({
                        "name": crop.get("name", str(crop)),
                        "area": crop.get("surface", crop.get("area", 1))
                    })
                else:
                    crops_data.append({
                        "name": getattr(crop, "name", str(crop)),
                        "area": getattr(crop, "surface", getattr(crop, "area", 1))
                    })

            farm_data = {
                "region": region,
                "crops": crops_data,
                "total_area": user.total_surface or 10,
                "water_available": 500,
                "budget": 100000,
                "soil_type": soil_type
            }
            optimization = self.optimize_resources(farm_data)

            # Format les risques correctement
            formatted_risks = []
            for risk in risks[:3]:  # Top 3 risques
                if isinstance(risk, dict):
                    formatted_risks.append(f"⚠️ {risk.get('description', str(risk))}")
                else:
                    formatted_risks.append(f"⚠️ {str(risk)}")

            return {
                "crop_recommendation": f"🌾 Culture recommandée: {crop_rec.crop_name} (Confiance: {crop_rec.confidence_score:.1%})",
                "yield_prediction": f"📊 Rendement prévu: {yield_pred.get('predicted_yield', 'N/A')} tonnes/ha",
                "risks": formatted_risks,
                "optimizations": [
                    f"💧 {optimization.get('water_optimization', 'Optimisation eau disponible')}",
                    f"🧪 {optimization.get('fertilizer_optimization', 'Optimisation fertilisants disponible')}",
                    f"🌱 {optimization.get('crop_rotation', 'Rotation culturale recommandée')}"
                ]
            }

        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {e}")
            return {
                "crop_recommendation": "Service IA temporairement indisponible",
                "yield_prediction": "N/A",
                "risks": [],
                "optimizations": []
            }

# ==========================================
# INSTANCE GLOBALE DU SERVICE
# ==========================================

# Créer l'instance globale d'AgroBrain
agro_brain = AgroBrainService()

# ==========================================
# FONCTIONS UTILITAIRES POUR L'API
# ==========================================

def get_crop_recommendation(region: str, soil_type: str, season: str,
                          temperature: float = None, rainfall: float = None) -> Dict:
    """Fonction utilitaire pour l'API"""
    recommendation = agro_brain.recommend_crop(region, soil_type, season, temperature, rainfall)
    return {
        "crop": recommendation.crop_name,
        "confidence": recommendation.confidence_score,
        "expected_yield": recommendation.expected_yield,
        "water_requirement": recommendation.water_requirement,
        "fertilizer_needs": recommendation.fertilizer_needs,
        "risk_factors": recommendation.risk_factors,
        "adaptation_tips": recommendation.adaptation_tips
    }

def get_yield_prediction(crop: str, region: str, soil_type: str,
                        rainfall: float, fertilizer_amount: float,
                        temperature: float = None) -> Dict:
    """Fonction utilitaire pour l'API"""
    return agro_brain.predict_yield(crop, region, soil_type, rainfall, fertilizer_amount, temperature)

def get_risk_alerts(region: str, crop: str, conditions: Dict) -> List[Dict]:
    """Fonction utilitaire pour l'API"""
    return agro_brain.detect_risks(region, crop, conditions)

def get_resource_optimization(farm_data: Dict) -> Dict:
    """Fonction utilitaire pour l'API"""
    return agro_brain.optimize_resources(farm_data)

# ==========================================
# TESTS ET VALIDATION
# ==========================================

if __name__ == "__main__":
    # Tests du service
    print("🧠 Test d'AgroBrain Service")

    # Test de recommandation
    rec = agro_brain.recommend_crop("Sikasso", "sableux", "hivernage")
    print(f"🌾 Recommandation pour Sikasso: {rec.crop_name} (confiance: {rec.confidence_score:.2f})")

    # Test de prédiction de rendement
    pred = agro_brain.predict_yield("mil", "Sikasso", "sableux", 800, 80)
    print(f"📊 Rendement prédit pour le mil: {pred['predicted_yield']:.2f} tonnes/ha")

    # Test de détection de risques
    risks = agro_brain.detect_risks("Sikasso", "mil", {"temperature": 38, "humidity": 30, "rainfall": 5})
    print(f"⚠️ Risques détectés: {len(risks)}")

    print("✅ AgroBrain Service opérationnel !")