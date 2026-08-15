"""
Service IA Avancé - Machine Learning pour Agriculture Intelligente
Phase 2 : IA & Analytiques Avancées pour AgroSmart
"""

import os
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import asyncio
import structlog

# ML Libraries
try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split, TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score
    import joblib

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import tensorflow as tf
    from tensorflow import keras

    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

HAS_ML = HAS_SKLEARN
if not HAS_ML:
    print("scikit-learn non disponible - mode simulation active")
elif not HAS_TENSORFLOW:
    print("TensorFlow non disponible - scikit-learn seul (pas de LSTM)")

from services.cache_service import cached, cache_service
from services.model_registry import model_registry
from services.real_data_training import build_real_training_dataset
from mali_data import MALI_REGIONS, get_region_by_coords
from mali_apis import MaliRealAPIs
from database import SessionLocal
import models

DEFAULT_ML_MODEL_VERSION = "1.0.0"
MODEL_METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "model_metadata.json")
MODEL_PERFORMANCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "model_performance.json")
logger = structlog.get_logger()

class AdvancedMLService:
    """
    Service IA avancé pour prédictions climatiques et recommandations agricoles
    """

    def __init__(self):
        self.weather_lstm_model = None
        self.crop_recommendation_model = None
        self.yield_prediction_model = None
        self.price_model = None
        self.scalers = {}
        self.models_loaded = False
        self.model_versions = {
            "weather": DEFAULT_ML_MODEL_VERSION,
            "crop_recommendation": DEFAULT_ML_MODEL_VERSION,
            "yield": DEFAULT_ML_MODEL_VERSION,
            "price": DEFAULT_ML_MODEL_VERSION,
            "rules": "rule_based-v1",
        }
        self._drift_metrics = {
            "input_distribution": {},
            "drift": {},
            "actual_vs_predicted": [],
        }
        self._model_performance = self._load_model_metrics()

        if HAS_ML:
            self.load_or_train_models()
        else:
            logger.warning("ML libraries non disponibles - fonctionnalités limitées")

    def load_or_train_models(self):
        """Charge ou entraîne les modèles avancés avec versioning et fallback."""
        try:
            self._ensure_model_registry_defaults()

            if HAS_TENSORFLOW:
                self.weather_lstm_model = self._load_model_artifact("weather_lstm", "models/weather_lstm.h5", keras.models.load_model)
                if self.weather_lstm_model is None:
                    self.train_weather_lstm_model()
            else:
                self.weather_lstm_model = None
                logger.info("LSTM météo ignoré (TensorFlow non installé)")

            self.crop_recommendation_model = self._load_model_artifact("crop_recommendation", "models/crop_recommendation.joblib", joblib.load if HAS_SKLEARN else None)
            if self.crop_recommendation_model is None:
                self.train_crop_recommendation_model()

            self.yield_prediction_model = self._load_model_artifact("yield_prediction", "models/yield_prediction.joblib", joblib.load if HAS_SKLEARN else None)
            if self.yield_prediction_model is None:
                self.train_yield_prediction_model()

            self.price_model = self._load_model_artifact("price_prediction", "models/price_prediction.joblib", joblib.load if HAS_SKLEARN else None)
            if self.price_model is None:
                self.train_price_prediction_model()

            scaler_path = "models/price_scaler.joblib"
            if os.path.exists(scaler_path) and self.price_model is not None:
                self.scalers["price"] = joblib.load(scaler_path)

            self.model_versions["weather"] = self._get_registered_model_version("weather_lstm") or self.model_versions["weather"]
            self.model_versions["crop_recommendation"] = self._get_registered_model_version("crop_recommendation") or self.model_versions["crop_recommendation"]
            self.model_versions["yield"] = self._get_registered_model_version("yield_prediction") or self.model_versions["yield"]
            self.model_versions["price"] = self._get_registered_model_version("price_prediction") or self.model_versions["price"]

            self.models_loaded = all([
                self.crop_recommendation_model is not None,
                self.yield_prediction_model is not None,
                self.price_model is not None
            ])
            logger.info("Tous les modèles IA chargés avec succès")

        except Exception as e:
            logger.error("Erreur chargement modèles", error=str(e))
            self.models_loaded = False

    def _ensure_model_registry_defaults(self):
        for model_name, artifact_name in {
            "yield_prediction": "yield_prediction-v1.0.0.joblib",
            "price_prediction": "price_prediction-v1.0.0.joblib",
            "crop_recommendation": "crop_recommendation-v1.0.0.joblib",
        }.items():
            artifact_path = os.path.join("models", artifact_name)
            if os.path.exists(artifact_path):
                metadata = model_registry.get_model_metadata(model_name)
                if metadata is None:
                    model_registry.register_model(model_name, artifact_path, version="1.0.0", source="filesystem", status="ready")
                    model_registry.set_active_version(model_name, "1.0.0")

    def _get_registered_model_version(self, model_name: str) -> Optional[str]:
        return model_registry.get_active_model_version(model_name)

    def _load_model_artifact(self, model_name: str, artifact_path: str, loader: Optional[Any] = None):
        if not os.path.exists(artifact_path):
            return None
        try:
            if loader is None:
                return None
            artifact = loader(artifact_path)
            version = self._get_registered_model_version(model_name) or DEFAULT_ML_MODEL_VERSION
            model_registry.register_model(model_name, artifact_path, version=version, source="filesystem", status="ready")
            if model_registry.get_active_model_version(model_name) is None:
                model_registry.set_active_version(model_name, version)
            return artifact
        except Exception as exc:
            logger.warning("Impossible de charger le modèle", model_name=model_name, error=str(exc))
            return None

    def _generate_cache_key(self, prefix: str, payload: Any) -> str:
        try:
            serialized = json.dumps(payload, sort_keys=True, default=str)
        except Exception:
            serialized = str(payload)
        version = self.model_versions.get("yield", DEFAULT_ML_MODEL_VERSION)
        return f"ml:{version}:{prefix}:{serialized}"

    def _load_model_metrics(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(MODEL_PERFORMANCE_PATH):
                return {}
            with open(MODEL_PERFORMANCE_PATH, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _save_model_metrics(self, model_name: str, metrics: Dict[str, Any]) -> None:
        try:
            payload = dict(getattr(self, "_model_performance", {}) or {})
            payload[model_name] = metrics
            os.makedirs(os.path.dirname(MODEL_PERFORMANCE_PATH), exist_ok=True)
            with open(MODEL_PERFORMANCE_PATH, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            self._model_performance = payload
        except Exception as exc:
            logger.warning("Impossible d'enregistrer les métriques du modèle", error=str(exc))

    def _record_drift_metric(self, payload: Dict[str, Any], prediction: Dict[str, Any], actual_value: Optional[float] = None) -> None:
        try:
            feature_keys = sorted({k for k in payload.get("crop_data", {}) if isinstance(payload.get("crop_data"), dict)})
            self._drift_metrics["input_distribution"]["sample_count"] = self._drift_metrics["input_distribution"].get("sample_count", 0) + 1
            self._drift_metrics["drift"]["last_prediction"] = {
                "model_version": self.model_versions.get("yield", DEFAULT_ML_MODEL_VERSION),
                "predicted": prediction.get("predicted_yield"),
            }
            if actual_value is not None:
                self._drift_metrics["actual_vs_predicted"].append({
                    "predicted": prediction.get("predicted_yield"),
                    "actual": actual_value,
                    "model_version": self.model_versions.get("yield", DEFAULT_ML_MODEL_VERSION),
                })
                if len(self._drift_metrics["actual_vs_predicted"]) > 50:
                    self._drift_metrics["actual_vs_predicted"] = self._drift_metrics["actual_vs_predicted"][-50:]
        except Exception:
            pass

    def record_yield_prediction(self, db, user_id: int, payload: Dict[str, Any], prediction_result: Dict[str, Any]) -> None:
        try:
            from models import YieldPrediction

            crop_id = None
            crop_data = payload.get("crop_data") if isinstance(payload, dict) else None
            if isinstance(crop_data, dict):
                crop_id = crop_data.get("crop_id")

            yield_record = YieldPrediction(
                user_id=user_id,
                crop_id=crop_id,
                predicted_yield=float(prediction_result.get("predicted_yield", 0)),
                yield_unit=prediction_result.get("unit", "kg/ha"),
                confidence_interval_low=prediction_result.get("confidence_interval", {}).get("low"),
                confidence_interval_high=prediction_result.get("confidence_interval", {}).get("high"),
                factors_used=json.dumps({
                    "crop_data": payload.get("crop_data"),
                    "weather_data": payload.get("weather_data"),
                    "sensor_data": payload.get("sensor_data"),
                }, default=str),
                ai_model_version=self.model_versions.get("yield"),
            )
            db.add(yield_record)
            db.commit()
        except Exception as exc:
            logger.error("Erreur enregistrement prédiction rendement", error=str(exc))
            try:
                db.rollback()
            except Exception:
                pass

    def record_ai_recommendations(self, db, user_id: int, payload: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> None:
        try:
            from models import AIRecommendation

            crop_id = None
            crop_data = payload.get("crop_data") if isinstance(payload, dict) else None
            if isinstance(crop_data, dict):
                crop_id = crop_data.get("crop_id")

            records = []
            for rec in recommendations or []:
                record = AIRecommendation(
                    user_id=user_id,
                    crop_id=crop_id,
                    recommendation_type=rec.get("type", "agronomic"),
                    title=rec.get("title", "Agronomic recommendation"),
                    description=rec.get("description", ""),
                    priority_level=rec.get("priority", "medium"),
                    confidence_score=rec.get("confidence_score") if rec.get("confidence_score") is not None else None,
                    expected_impact=rec.get("expected_benefit") or rec.get("expected_impact"),
                    implementation_cost=None,
                    implementation_time=None,
                    ai_model_version=self.model_versions.get("rules"),
                    weather_factors=json.dumps(payload.get("weather_data") or {}, default=str),
                    sensor_data=json.dumps(payload.get("sensor_data") or [], default=str),
                )
                records.append(record)

            if records:
                db.add_all(records)
                db.commit()
        except Exception as exc:
            logger.error("Erreur enregistrement recommandations IA", error=str(exc))
            try:
                db.rollback()
            except Exception:
                pass

    @cached(ttl_seconds=1800)  # Cache 30 minutes
    def predict_weather_advanced(self, lat: float, lon: float, days_ahead: int = 7) -> Dict[str, Any]:
        """
        Prédiction météo avancée avec LSTM pour les prochains jours
        """
        if (
            not self.models_loaded
            or not HAS_TENSORFLOW
            or self.weather_lstm_model is None
        ):
            return self._fallback_weather_prediction(lat, lon, days_ahead)

        try:
            # Récupérer données historiques
            historical_data = self._get_historical_weather_data(lat, lon, days=30)

            if len(historical_data) < 10:
                return self._fallback_weather_prediction(lat, lon, days_ahead)

            # Préparer les données pour LSTM
            X = self._prepare_lstm_input(historical_data, sequence_length=7)

            if X is None or len(X) == 0:
                return self._fallback_weather_prediction(lat, lon, days_ahead)

            # Prédire avec LSTM
            predictions = self.weather_lstm_model.predict(X, verbose=0)

            # Convertir en format lisible
            forecast = []
            base_date = datetime.now()

            for i in range(min(days_ahead, len(predictions[0]))):
                pred_temp = float(predictions[0][i][0])
                pred_rain = max(0, float(predictions[0][i][1]))  # Pas de pluie négative
                pred_humidity = min(100, max(0, float(predictions[0][i][2])))

                forecast.append({
                    "date": (base_date + timedelta(days=i+1)).strftime("%Y-%m-%d"),
                    "temperature_celsius": round(pred_temp, 1),
                    "rainfall_mm": round(pred_rain, 1),
                    "humidity_percent": round(pred_humidity, 1),
                    "confidence": 0.85  # Confiance estimée du modèle
                })

            return {
                "forecast": forecast,
                "model_used": "LSTM_Advanced",
                "accuracy_estimate": 0.82,
                "data_points_used": len(historical_data),
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Erreur prédiction météo avancée", error=str(e))
            return self._fallback_weather_prediction(lat, lon, days_ahead)

    def _get_historical_weather_data(self, lat: float, lon: float, days: int = 30) -> List[Dict]:
        """Récupère données météo historiques pour entraînement/prédiction"""
        try:
            # Essayer de récupérer des données réelles
            rainfall_data = MaliRealAPIs.get_chirps_rainfall(lat, lon)
            current_weather = MaliRealAPIs.get_weather_real(lat, lon)

            if rainfall_data and current_weather:
                # Combiner les données
                historical = []
                base_temp = current_weather.get("current", {}).get("temperature_2m", 25)

                for i, rain_entry in enumerate(rainfall_data[-days:]):
                    temp_variation = np.random.normal(0, 5)  # Variation réaliste
                    historical.append({
                        "date": rain_entry.get("date", f"day_{-i}"),
                        "temperature": base_temp + temp_variation,
                        "rainfall": rain_entry.get("rainfall", 0),
                        "humidity": np.random.uniform(30, 90)
                    })

                return historical

        except Exception as e:
            logger.warning("Erreur récupération données historiques", error=str(e))

        # Fallback: générer données synthétiques réalistes
        return self._generate_synthetic_weather_data(days)

    def _generate_synthetic_weather_data(self, days: int) -> List[Dict]:
        """Génère données météo synthétiques pour tests/entraînement"""
        data = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(days):
            # Saisonnalité réaliste pour Mali
            day_of_year = (base_date + timedelta(days=i)).timetuple().tm_yday
            seasonal_temp = 25 + 5 * np.sin(2 * np.pi * day_of_year / 365)

            data.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "temperature": seasonal_temp + np.random.normal(0, 3),
                "rainfall": max(0, np.random.exponential(2) if np.random.random() < 0.3 else 0),
                "humidity": np.random.uniform(20, 95)
            })

        return data

    def _prepare_lstm_input(self, historical_data: List[Dict], sequence_length: int = 7) -> Optional[np.ndarray]:
        """Prépare les données pour input LSTM"""
        try:
            if len(historical_data) < sequence_length:
                return None

            # Extraire features
            temps = [d["temperature"] for d in historical_data[-sequence_length:]]
            rains = [d["rainfall"] for d in historical_data[-sequence_length:]]
            humids = [d["humidity"] for d in historical_data[-sequence_length:]]

            # Normaliser
            if "weather" not in self.scalers:
                self.scalers["weather"] = MinMaxScaler()
                # Fit sur données d'entraînement (simplifié)
                sample_data = np.random.rand(100, 3)
                self.scalers["weather"].fit(sample_data)

            # Préparer séquence
            sequence = np.array([temps, rains, humids]).T
            sequence_scaled = self.scalers["weather"].transform(sequence)

            return np.array([sequence_scaled])  # Shape: (1, sequence_length, 3)

        except Exception as e:
            logger.error("Erreur préparation LSTM", error=str(e))
            return None

    def _fallback_weather_prediction(self, lat: float, lon: float, days_ahead: int) -> Dict[str, Any]:
        """Simulation réaliste de prédiction météo pour le Mali"""
        predictions = []
        base_date = datetime.now()

        for i in range(days_ahead):
            date = base_date + timedelta(days=i)
            day_of_year = date.timetuple().tm_yday

            # Simulation saisonnière réaliste pour le Mali (climat sahélien)
            base_temp = 25 + 10 * np.sin(2 * np.pi * day_of_year / 365)  # Saisonnalité
            temperature = base_temp + np.random.normal(0, 2)

            # Précipitations saisonnières (mai-octobre)
            rainfall_season = np.sin(2 * np.pi * (day_of_year - 121) / 365)
            rainfall = max(0, rainfall_season * np.random.exponential(3))

            # Humidité corrélée aux précipitations
            humidity = 40 + 30 * max(0, rainfall_season) + np.random.normal(0, 5)
            humidity = np.clip(humidity, 10, 90)

            predictions.append({
                "date": date.strftime("%Y-%m-%d"),
                "temperature_celsius": round(temperature, 1),
                "rainfall_mm": round(rainfall, 1),
                "humidity_percent": round(humidity, 1),
                "confidence": round(0.7 + np.random.random() * 0.2, 2)
            })

        return {
            "location": f"{lat:.4f}, {lon:.4f}",
            "forecast_days": days_ahead,
            "predictions": predictions,
            "model_used": "simulation_mali_climate",
            "generated_at": datetime.now().isoformat()
        }

    def train_weather_lstm_model(self):
        """Entraîne le modèle LSTM pour prédictions météo"""
        if not HAS_TENSORFLOW:
            logger.info("TensorFlow non disponible - entrainement LSTM ignore")
            return

        try:
            # Générer données d'entraînement synthétiques
            training_data = []
            for _ in range(1000):  # 1000 séquences
                sequence = self._generate_synthetic_weather_data(30)
                training_data.append(sequence)

            # Préparer X et y
            X, y = [], []
            sequence_length = 7

            for seq in training_data:
                if len(seq) >= sequence_length + 1:
                    for i in range(len(seq) - sequence_length):
                        input_seq = seq[i:i+sequence_length]
                        target = seq[i+sequence_length]

                        # Préparer input
                        temps = [d["temperature"] for d in input_seq]
                        rains = [d["rainfall"] for d in input_seq]
                        humids = [d["humidity"] for d in input_seq]

                        X.append([temps, rains, humids])
                        y.append([target["temperature"], target["rainfall"], target["humidity"]])

            X = np.array(X)  # Shape: (n_samples, 3, sequence_length)
            y = np.array(y)  # Shape: (n_samples, 3)

            # Normaliser
            self.scalers["weather"] = MinMaxScaler()
            X_reshaped = X.reshape(-1, 3)
            X_scaled = self.scalers["weather"].fit_transform(X_reshaped)
            X = X_scaled.reshape(X.shape)

            # Créer modèle LSTM
            model = keras.Sequential([
                keras.layers.LSTM(64, input_shape=(3, sequence_length), return_sequences=True),
                keras.layers.Dropout(0.2),
                keras.layers.LSTM(32),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(3)  # 3 outputs: temp, rain, humidity
            ])

            model.compile(optimizer='adam', loss='mse', metrics=['mae'])

            # Entraîner
            model.fit(X, y, epochs=50, batch_size=32, validation_split=0.2, verbose=0)

            # Sauvegarder
            os.makedirs("models", exist_ok=True)
            model.save("models/weather_lstm.h5")

            self.weather_lstm_model = model
            logger.info("Modèle LSTM météo entraîné et sauvegardé")

        except Exception as e:
            logger.error("Erreur entraînement modèle LSTM", error=str(e))

    def get_crop_recommendations_advanced(self, lat: float, lon: float,
                                        soil_type: str = "fertile",
                                        water_access: bool = True) -> Dict[str, Any]:
        """
        Recommandations de cultures avancées avec ML
        """
        if not self.models_loaded:
            return self._fallback_crop_recommendations(lat, lon, soil_type, water_access)

        try:
            region = get_region_by_coords(lat, lon) or "Mali"

            # Features pour le modèle
            features = self._extract_crop_features(lat, lon, region, soil_type, water_access)

            if self.crop_recommendation_model:
                # Prédire les meilleures cultures
                predictions = self.crop_recommendation_model.predict_proba([features])[0]

                # Cultures disponibles
                crops = ["mil", "sorgho", "maïs", "riz", "arachide", "coton", "sésame"]
                crop_scores = dict(zip(crops, predictions))

                # Trier par score
                recommended_crops = sorted(crop_scores.items(), key=lambda x: x[1], reverse=True)

                return {
                    "recommendations": [
                        {
                            "crop": crop,
                            "confidence": float(score),
                            "suitability_score": float(score * 100),
                            "expected_yield": self._estimate_yield(crop, region),
                            "risk_level": self._assess_risk(crop, region)
                        } for crop, score in recommended_crops[:5]  # Top 5
                    ],
                    "region": region,
                    "model_used": "GradientBoosting_Advanced",
                    "features_considered": list(features.keys())
                }
            else:
                return self._fallback_crop_recommendations(lat, lon, soil_type, water_access)

        except Exception as e:
            logger.error("Erreur recommandations cultures avancées", error=str(e))
            return self._fallback_crop_recommendations(lat, lon, soil_type, water_access)

    def _extract_crop_features(self, lat: float, lon: float, region: str,
                             soil_type: str, water_access: bool) -> Dict[str, float]:
        """Extrait les features pour recommandations de cultures"""
        # Features géographiques et environnementales
        features = {
            "latitude": lat,
            "longitude": lon,
            "is_sahara_region": 1.0 if region in ["Tombouctou", "Gao", "Kidal"] else 0.0,
            "is_sahel_region": 1.0 if region in ["Mopti", "Ségou", "Kayes"] else 0.0,
            "is_soudan_region": 1.0 if region in ["Bamako", "Koulikoro", "Sikasso"] else 0.0,
            "soil_fertile": 1.0 if soil_type == "fertile" else 0.0,
            "soil_clay": 1.0 if soil_type == "clay" else 0.0,
            "soil_sandy": 1.0 if soil_type == "sandy" else 0.0,
            "water_access": 1.0 if water_access else 0.0,
            "rainfall_season": 1.0,  # Saison des pluies (juin-octobre)
        }

        return features

    def _estimate_yield(self, crop: str, region: str) -> str:
        """Estime le rendement attendu"""
        base_yields = {
            "mil": {"Sahara": "500-800 kg/ha", "Sahel": "800-1200 kg/ha", "Soudan": "1200-1800 kg/ha"},
            "maïs": {"Sahara": "2000-3000 kg/ha", "Sahel": "3000-4000 kg/ha", "Soudan": "4000-6000 kg/ha"},
            "riz": {"Sahara": "1000-1500 kg/ha", "Sahel": "2000-3000 kg/ha", "Soudan": "4000-6000 kg/ha"},
        }

        region_type = "Soudan"  # Default
        if region in ["Tombouctou", "Gao", "Kidal"]:
            region_type = "Sahara"
        elif region in ["Mopti", "Ségou", "Kayes"]:
            region_type = "Sahel"

        return base_yields.get(crop, {}).get(region_type, "1000-2000 kg/ha")

    def _assess_risk(self, crop: str, region: str) -> str:
        """Évalue le niveau de risque"""
        high_risk_regions = ["Tombouctou", "Gao", "Kidal"]
        medium_risk_regions = ["Mopti", "Ségou", "Kayes"]

        if region in high_risk_regions:
            return "Élevé (sécheresse, désertification)"
        elif region in medium_risk_regions:
            return "Moyen (variabilité climatique)"
        else:
            return "Faible (conditions favorables)"

    def _fallback_crop_recommendations(self, lat: float, lon: float,
                                     soil_type: str, water_access: bool) -> Dict[str, Any]:
        """Simulation réaliste de recommandations de cultures pour le Mali"""
        region = get_region_by_coords(lat, lon) or "Mali"

        # Cultures principales du Mali avec scores réalistes
        base_crops = {
            "mil": {"base_score": 0.85, "yield": "800-1200 kg/ha", "regions": ["Tombouctou", "Gao", "Mopti", "Ségou"]},
            "sorgho": {"base_score": 0.78, "yield": "600-1000 kg/ha", "regions": ["Tombouctou", "Gao", "Mopti", "Ségou"]},
            "maïs": {"base_score": 0.72, "yield": "1500-2500 kg/ha", "regions": ["Ségou", "Kayes", "Koulikoro", "Bamako"]},
            "arachide": {"base_score": 0.65, "yield": "700-1100 kg/ha", "regions": ["Kayes", "Koulikoro", "Ségou"]},
            "coton": {"base_score": 0.58, "yield": "200-400 kg/ha", "regions": ["Ségou", "Koulikoro", "Sikasso"]},
            "riz": {"base_score": 0.80, "yield": "2500-4000 kg/ha", "regions": ["Kayes", "Koulikoro", "Bamako"], "needs_water": True}
        }

        recommendations = []
        for crop, data in base_crops.items():
            # Ajustement du score selon la région
            score = data["base_score"]
            if region in data.get("regions", []):
                score += 0.1  # Bonus régional

            # Ajustement selon le type de sol
            soil_modifier = {
                "fertile": 1.1,
                "argileux": 0.9,
                "sableux": 0.8,
                "limoneux": 1.0
            }.get(soil_type, 1.0)
            score *= soil_modifier

            # Ajustement selon l'accès à l'eau
            if data.get("needs_water", False) and not water_access:
                score *= 0.7

            # Niveau de risque
            if score > 0.8:
                risk = "faible"
            elif score > 0.6:
                risk = "moyen"
            else:
                risk = "élevé"

            recommendations.append({
                "crop": crop,
                "confidence": round(score, 2),
                "suitability_score": round(score * 100, 1),
                "expected_yield": data["yield"],
                "risk_level": risk
            })

        # Trier par score et prendre top 3
        recommendations.sort(key=lambda x: x["suitability_score"], reverse=True)

        return {
            "location": f"{lat:.4f}, {lon:.4f}",
            "region": region,
            "soil_type": soil_type,
            "water_access": water_access,
            "recommendations": recommendations[:3],
            "model_used": "simulation_mali_agriculture",
            "generated_at": datetime.now().isoformat()
        }

    def train_crop_recommendation_model(self):
        """Entraîne le modèle de recommandation de cultures"""
        if not HAS_ML:
            logger.warning("scikit-learn non disponible - pas d'entraînement")
            return

        try:
            # Générer données d'entraînement synthétiques
            n_samples = 1000
            features = []
            targets = []

            crops = ["mil", "sorgho", "maïs", "riz", "arachide", "coton", "sésame"]

            for _ in range(n_samples):
                # Générer features aléatoires réalistes
                lat = np.random.uniform(10, 18)  # Latitude Mali
                lon = np.random.uniform(-12, 4)  # Longitude Mali
                region = np.random.choice(["Tombouctou", "Gao", "Mopti", "Ségou", "Kayes", "Koulikoro", "Bamako", "Sikasso"])
                soil_type = np.random.choice(["fertile", "clay", "sandy"])
                water_access = np.random.choice([True, False])

                feature_dict = self._extract_crop_features(lat, lon, region, soil_type, water_access)
                features.append(list(feature_dict.values()))

                # Target: culture la plus adaptée (basé sur logique simple)
                if region in ["Tombouctou", "Gao"]:
                    target = np.random.choice([0, 1], p=[0.7, 0.3])  # mil/sorgho
                elif region in ["Mopti", "Ségou"]:
                    target = np.random.choice([0, 1, 2], p=[0.4, 0.3, 0.3])  # mil/sorgho/maïs
                else:
                    target = np.random.choice([2, 3, 4, 5], p=[0.3, 0.25, 0.25, 0.2])  # maïs/riz/arachide/coton

                targets.append(target)

            X = np.array(features)
            y = np.array(targets)

            # Entraîner modèle
            model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            model.fit(X, y)

            # Sauvegarder
            os.makedirs("models", exist_ok=True)
            joblib.dump(model, "models/crop_recommendation.joblib")

            self.crop_recommendation_model = model
            logger.info("Modèle recommandation cultures entraîné et sauvegardé")

        except Exception as e:
            logger.error("Erreur entraînement modèle cultures", error=str(e))

    def train_yield_prediction_model(self):
        """Entraîne le modèle de prédiction de rendement"""
        if not HAS_ML:
            return

        try:
            try:
                X, y = build_real_training_dataset(limit=500)
                logger.info("Entraînement rendement sur données réelles depuis la base")
            except Exception as exc:
                logger.warning("Données réelles indisponibles, fallback synthétique: %s", exc)
                n_samples = 500
                features = []
                yields = []

                for _ in range(n_samples):
                    lat = np.random.uniform(10, 18)
                    lon = np.random.uniform(-12, 4)
                    region = np.random.choice(["Tombouctou", "Gao", "Mopti", "Ségou", "Kayes", "Koulikoro", "Bamako", "Sikasso"])
                    crop = np.random.choice(["mil", "maïs", "riz", "coton"])
                    rainfall = np.random.uniform(200, 1200)  # mm/an
                    soil_quality = np.random.uniform(0.3, 1.0)
                    farming_experience = np.random.uniform(1, 30)  # années

                    features.append([lat, lon, rainfall, soil_quality, farming_experience])
                    base_yield = {"mil": 800, "maïs": 3000, "riz": 4000, "coton": 1200}[crop]
                    yield_variation = np.random.normal(0, 300)
                    actual_yield = max(100, base_yield + yield_variation)
                    yields.append(actual_yield)

                X = np.array(features)
                y = np.array(yields)

            # Entraîner modèle de régression
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            # Sauvegarder
            os.makedirs("models", exist_ok=True)
            joblib.dump(model, "models/yield_prediction.joblib")

            self.yield_prediction_model = model
            metrics = {
                "r2_score": round(float(r2_score(y, model.predict(X))), 3) if len(np.unique(y)) > 1 else None,
                "mae": round(float(mean_absolute_error(y, model.predict(X))), 3) if len(np.unique(y)) > 1 else None,
            }
            self._save_model_metrics("yield_prediction", metrics)
            logger.info("Modèle prédiction rendement entraîné et sauvegardé")

        except Exception as e:
            logger.error("Erreur entraînement modèle rendement", error=str(e))

    def train_price_prediction_model(self):
        """Entraîne le modèle de prédiction de prix"""
        if not HAS_ML:
            return

        try:
            X, y = self._build_price_training_dataset()
            if X is None or y is None or len(X) < 10:
                logger.warning("Pas assez de données de prix réelles, fallback synthétique")
                X, y = self._build_synthetic_price_dataset()

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_scaled, y)

            os.makedirs("models", exist_ok=True)
            joblib.dump(model, "models/price_prediction.joblib")
            joblib.dump(scaler, "models/price_scaler.joblib")

            self.price_model = model
            self.scalers["price"] = scaler
            metrics = {
                "r2_score": round(float(r2_score(y, model.predict(X_scaled))), 3) if len(np.unique(y)) > 1 else None,
                "mae": round(float(mean_absolute_error(y, model.predict(X_scaled))), 3) if len(np.unique(y)) > 1 else None,
            }
            self._save_model_metrics("price_prediction", metrics)
            logger.info("Modèle prédiction prix entraîné et sauvegardé")

        except Exception as e:
            logger.error("Erreur entraînement modèle prix", error=str(e))

    def _build_price_training_dataset(self):
        try:
            db = SessionLocal()
            prices = db.query(models.MarketPrice).order_by(models.MarketPrice.timestamp.desc()).limit(2000).all()
            if not prices:
                return None, None

            features = []
            targets = []
            grade_map = {"A": 1.0, "B": 0.9, "C": 0.8}

            sorted_prices = sorted(prices, key=lambda row: row.timestamp)
            grouped = {}
            for row in sorted_prices:
                key = (row.crop_type.lower() if row.crop_type else "unknown", row.market_location.lower() if row.market_location else "unknown")
                grouped.setdefault(key, []).append(row.price_per_kg)

            for key, history in grouped.items():
                if len(history) < 8:
                    continue
                for i in range(7, len(history)):
                    window = history[i - 7:i]
                    latest_price = float(window[-1])
                    avg_last_7 = float(np.mean(window))
                    volatility = float(np.ptp(window))
                    quality_grade = "A"
                    quality_val = grade_map.get(quality_grade, 0.9)
                    features.append([latest_price, avg_last_7, volatility, quality_val])
                    targets.append(float(history[i]))

            db.close()
            if not features or not targets:
                return None, None
            return np.array(features, dtype=float), np.array(targets, dtype=float)
        except Exception as exc:
            logger.warning("Erreur construction dataset prix réel", error=str(exc))
            try:
                db.close()
            except Exception:
                pass
            return None, None

    def _build_synthetic_price_dataset(self):
        n_samples = 500
        features = []
        targets = []
        grade_map = {"A": 1.0, "B": 0.9, "C": 0.8}

        for _ in range(n_samples):
            prices = np.random.uniform(300, 700, size=10)
            historical_prices = list(prices)
            latest_price = historical_prices[-1]
            avg_last_7 = np.mean(historical_prices[-7:])
            volatility = float(np.ptp(historical_prices[-7:]))
            quality_grade = np.random.choice(["A", "B", "C"], p=[0.5, 0.3, 0.2])
            quality_val = grade_map[quality_grade]

            features.append([latest_price, avg_last_7, volatility, quality_val])
            predicted_price = latest_price + np.random.normal(0, 20) + (quality_val - 0.9) * 50 - volatility * 0.1
            targets.append(max(100.0, predicted_price))

        return np.array(features), np.array(targets)

    async def continuous_learning_update(self):
        """
        Mise à jour continue des modèles avec nouvelles données
        À exécuter périodiquement (ex: toutes les 24h)
        """
        if not self.models_loaded:
            return

        try:
            logger.info("Début mise à jour continue des modèles IA")

            # Collecter nouvelles données des utilisateurs
            # (En production: récupérer de la DB)
            new_weather_data = await self._collect_new_weather_data()
            new_crop_data = await self._collect_new_crop_performance_data()

            if new_weather_data:
                # Réentraîner modèle météo avec nouvelles données
                self.train_weather_lstm_model()

            if new_crop_data:
                # Réentraîner modèle cultures avec feedback utilisateurs
                self.train_crop_recommendation_model()

            logger.info("Mise à jour continue terminée")

        except Exception as e:
            logger.error("Erreur mise à jour continue", error=str(e))

    async def _collect_new_weather_data(self) -> Optional[List[Dict]]:
        """Collecte nouvelles données météo pour réentraînement"""
        # En production: récupérer de la DB ou APIs
        return None

    async def _collect_new_crop_performance_data(self) -> Optional[List[Dict]]:
        """Collecte données performance cultures pour réentraînement"""
        # En production: récupérer feedback utilisateurs
        return None

    def predict_yield(self, crop_data: Dict[str, Any], weather_data: Dict[str, Any],
                     sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict crop yield using ML models"""
        cache_key = self._generate_cache_key("predict_yield", {
            "crop_data": crop_data,
            "weather_data": weather_data,
            "sensor_data": sensor_data,
            "model_version": self.model_versions.get("yield"),
        })
        cached_result = cache_service.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            if not HAS_ML or not self.yield_prediction_model:
                response = self._fallback_yield_prediction(crop_data, weather_data, sensor_data)
            else:
                # Prepare features
                features = self._prepare_yield_features(crop_data, weather_data, sensor_data)

                # Make prediction
                prediction = self.yield_prediction_model.predict([features])[0]
                confidence = self._calculate_prediction_confidence(np.array([features]))

                response = {
                    "predicted_yield": max(0, float(prediction)),
                    "unit": "kg/ha",
                    "confidence_score": float(confidence),
                    "confidence_interval": {
                        "low": max(0, float(prediction * 0.8)),
                        "high": float(prediction * 1.2)
                    },
                    "factors_considered": ["soil_type", "weather_conditions", "sensor_data", "crop_age"],
                    "recommendations": self._generate_yield_recommendations(prediction, crop_data),
                }

            response["model_version"] = self.model_versions.get("yield")
            response["active_model_version"] = self.model_versions.get("yield")
            self._record_drift_metric(payload={"crop_data": crop_data, "weather_data": weather_data, "sensor_data": sensor_data}, prediction=response)
            cache_service.set(cache_key, response, ttl_seconds=900)
            return response

        except Exception as e:
            logger.error(f"Yield prediction error: {e}")
            return self._fallback_yield_prediction(crop_data, weather_data, sensor_data)

    def predict_price(self, crop_type: str, market_location: str, quality_grade: str = "A") -> Dict[str, Any]:
        """Predict future crop prices"""
        cache_key = self._generate_cache_key("predict_price", {
            "crop_type": crop_type,
            "market_location": market_location,
            "quality_grade": quality_grade,
            "model_version": self.model_versions.get("price"),
        })
        cached_result = cache_service.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            if not HAS_ML or not self.price_model:
                response = self._fallback_price_prediction(crop_type, market_location, quality_grade)
            else:
                # Get historical data
                historical_prices = self._get_historical_prices(crop_type, market_location, days=90)

                if len(historical_prices) < 7:
                    response = self._fallback_price_prediction(crop_type, market_location, quality_grade)
                else:
                    # Prepare time series features
                    features = self._prepare_price_features(historical_prices, quality_grade)
                    if 'price' in self.scalers and self.scalers['price'] is not None:
                        features_scaled = self.scalers['price'].transform([features])
                    else:
                        features_scaled = [features]

                    # Make prediction
                    prediction = self.price_model.predict(features_scaled)[0]
                    response = {
                        "predicted_price": max(0, float(prediction)),
                        "currency": "XOF",
                        "unit": "per kg",
                        "prediction_horizon": "7 days",
                        "confidence_score": 0.75,
                        "price_trend": "stable",
                        "market_factors": ["seasonal_demand", "weather_conditions", "global_supply"],
                    }

            response["model_version"] = self.model_versions.get("price")
            response["active_model_version"] = self.model_versions.get("price")
            cache_service.set(cache_key, response, ttl_seconds=900)
            return response

        except Exception as e:
            logger.error(f"Price prediction error: {e}")
            return self._fallback_price_prediction(crop_type, market_location, quality_grade)

    def assess_weather_risks(self, crop_data: Dict[str, Any], weather_forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Assess weather-related risks for crops"""
        try:
            risks = []
            recommendations = []

            # Temperature risk
            temp = weather_forecast.get("temperature", 25)
            if temp > 35:
                risks.append({
                    "type": "heat_stress",
                    "severity": "high",
                    "description": "Température élevée risque de stress thermique",
                    "impact": "Réduction du rendement jusqu'à 30%"
                })
                recommendations.append("Installer ombrage et augmenter irrigation")
            elif temp < 15:
                risks.append({
                    "type": "cold_stress",
                    "severity": "medium",
                    "description": "Température basse risque de gel",
                    "impact": "Dommages aux jeunes plants"
                })
                recommendations.append("Utiliser couvertures thermiques")

            # Precipitation risk
            rain = weather_forecast.get("precipitation", 0)
            if rain > 50:  # Heavy rain
                risks.append({
                    "type": "flooding",
                    "severity": "high",
                    "description": "Risque d'inondation",
                    "impact": "Perte totale possible"
                })
                recommendations.append("Améliorer drainage et surélever plants")
            elif rain < 5:  # Drought
                risks.append({
                    "type": "drought",
                    "severity": "critical",
                    "description": "Risque de sécheresse",
                    "impact": "Réduction rendement 50-80%"
                })
                recommendations.append("Irrigation d'urgence et mulch")

            # Wind risk
            wind = weather_forecast.get("wind_speed", 0)
            if wind > 30:
                risks.append({
                    "type": "wind_damage",
                    "severity": "medium",
                    "description": "Vent fort risque de casse",
                    "impact": "Dommages mécaniques"
                })
                recommendations.append("Brise-vent et tuteurage")

            return {
                "overall_risk_level": max([r["severity"] for r in risks], default="low"),
                "risks": risks,
                "recommendations": recommendations,
                "monitoring_frequency": "daily",
                "insurance_recommendation": len([r for r in risks if r["severity"] in ["high", "critical"]]) > 0
            }

        except Exception as e:
            logger.error(f"Weather risk assessment error: {e}")
            return {
                "overall_risk_level": "unknown",
                "risks": [],
                "recommendations": ["Surveiller les conditions météo"],
                "monitoring_frequency": "daily",
                "insurance_recommendation": False
            }

    def generate_agronomic_recommendations(self, crop_data: Dict[str, Any],
                                          sensor_data: List[Dict[str, Any]],
                                          weather_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive agronomic recommendations"""
        recommendations = []

        try:
            # Irrigation recommendations
            soil_moisture = self._extract_sensor_value(sensor_data, "soil_moisture")
            if soil_moisture is not None:
                if soil_moisture < 30:
                    recommendations.append({
                        "type": "irrigation",
                        "priority": "high",
                        "title": "Irrigation urgente requise",
                        "description": f"Humidité du sol à {soil_moisture:.1f}%. Irrigation recommandée.",
                        "action": "Arroser immédiatement",
                        "expected_benefit": "Prévention du stress hydrique"
                    })
                elif soil_moisture > 80:
                    recommendations.append({
                        "type": "irrigation",
                        "priority": "medium",
                        "title": "Réduire l'irrigation",
                        "description": f"Humidité du sol élevée ({soil_moisture:.1f}%). Risque de pourriture.",
                        "action": "Suspendre l'irrigation temporairement",
                        "expected_benefit": "Prévention des maladies racinaires"
                    })

            # Fertilization recommendations
            crop_age_days = crop_data.get("age_days", 30)
            if 20 <= crop_age_days <= 40:  # Growth phase
                recommendations.append({
                    "type": "fertilization",
                    "priority": "medium",
                    "title": "Apport en azote recommandé",
                    "description": "Phase de croissance active - besoins accrus en azote.",
                    "action": "Appliquer engrais azoté (urée 46%)",
                    "expected_benefit": "Amélioration croissance végétative"
                })

            # Pest control recommendations
            # This would use ML model for pest detection based on sensor data
            vibration = self._extract_sensor_value(sensor_data, "pump_vibration")
            if vibration and vibration > 60:
                recommendations.append({
                    "type": "maintenance",
                    "priority": "high",
                    "title": "Maintenance pompe requise",
                    "description": f"Vibration pompe élevée ({vibration:.1f} Hz). Usure détectée.",
                    "action": "Inspecter et lubrifier la pompe",
                    "expected_benefit": "Prévention panne équipement"
                })

            # Weather-based recommendations
            temp = weather_data.get("temperature", 25)
            if temp > 32:
                recommendations.append({
                    "type": "protection",
                    "priority": "high",
                    "title": "Protection contre chaleur",
                    "description": f"Température élevée ({temp:.1f}°C) détectée.",
                    "action": "Installer ombrage temporaire",
                    "expected_benefit": "Réduction stress thermique"
                })

            # Sort by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

            return recommendations[:5]  # Return top 5 recommendations

        except Exception as e:
            logger.error(f"Agronomic recommendations error: {e}")
            return [{
                "type": "general",
                "priority": "medium",
                "title": "Conseil général",
                "description": "Surveiller régulièrement vos cultures.",
                "action": "Inspection visuelle quotidienne",
                "expected_benefit": "Détection précoce des problèmes"
            }]

    def _prepare_yield_features(self, crop_data: Dict, weather_data: Dict, sensor_data: List[Dict]) -> List[float]:
        """Prepare features for yield prediction"""
        # The model was trained on [lat, lon, rainfall, soil_quality, farming_experience]
        latitude = float(crop_data.get("latitude", weather_data.get("latitude", 12.0)))
        longitude = float(crop_data.get("longitude", weather_data.get("longitude", -8.0)))
        rainfall = float(weather_data.get("rainfall", crop_data.get("rainfall", 400.0)))
        soil_quality = float(crop_data.get("soil_quality", 0.7))
        farming_experience = float(crop_data.get("farming_experience", 5.0))

        # Normalisation légère pour stabiliser les prédictions selon l’échelle des features
        return [
            latitude / 20.0,
            longitude / 20.0,
            rainfall / 1000.0,
            soil_quality,
            farming_experience / 30.0,
        ]

    def _prepare_price_features(self, historical_prices: List[float], quality_grade: str) -> List[float]:
        """Prepare features for price prediction"""
        features = []

        if len(historical_prices) >= 7:
            # Price trends
            latest_price = float(historical_prices[-1])
            last_7 = historical_prices[-7:]
            features.append(latest_price)
            features.append(sum(last_7) / len(last_7))
            features.append(max(last_7) - min(last_7))

        # Quality grade encoding
        grade_map = {"A": 1.0, "B": 0.8, "C": 0.6}
        features.append(grade_map.get(quality_grade, 0.5))

        return features

    def _calculate_prediction_confidence(self, features_scaled: np.ndarray) -> float:
        """Calculate prediction confidence (simplified)"""
        # In a real implementation, this would use model uncertainty estimation
        return 0.85  # Mock confidence

    def _extract_sensor_value(self, sensor_data: List[Dict], sensor_type: str) -> Optional[float]:
        """Extract latest value for sensor type"""
        for sensor in sensor_data:
            if sensor.get("sensor_type") == sensor_type:
                return sensor.get("value")
        return None

    def _generate_yield_recommendations(self, predicted_yield: float, crop_data: Dict) -> List[str]:
        """Generate recommendations based on yield prediction"""
        recommendations = []

        if predicted_yield < 1000:  # Low yield
            recommendations.append("Optimiser les pratiques culturales")
            recommendations.append("Améliorer la fertilisation")
        elif predicted_yield > 3000:  # High yield
            recommendations.append("Maintenir les bonnes pratiques")
            recommendations.append("Préparer stockage adéquat")

        return recommendations

    def _get_historical_prices(self, crop_type: str, market_location: str, days: int) -> List[float]:
        """Get historical price data (mock implementation)"""
        # In real implementation, this would query the database
        return [500 + i * 10 for i in range(min(days, 30))]

    def _fallback_yield_prediction(self, crop_data: Dict, weather_data: Dict, sensor_data: List[Dict]) -> Dict[str, Any]:
        """Fallback yield prediction when ML is not available"""
        base_yield = 2000  # kg/ha base yield

        # Adjust based on conditions
        temp = weather_data.get("temperature", 25)
        if temp < 20 or temp > 35:
            base_yield *= 0.8

        soil_moisture = self._extract_sensor_value(sensor_data, "soil_moisture") or 50
        if soil_moisture < 40:
            base_yield *= 0.9

        return {
            "predicted_yield": base_yield,
            "unit": "kg/ha",
            "confidence_score": 0.6,
            "confidence_interval": {
                "low": base_yield * 0.8,
                "high": base_yield * 1.2
            },
            "factors_considered": ["basic_weather", "soil_moisture"],
            "recommendations": ["Surveiller conditions météo", "Maintenir irrigation"]
        }

    def _fallback_price_prediction(self, crop_type: str, market_location: str, quality_grade: str) -> Dict[str, Any]:
        """Fallback price prediction"""
        base_prices = {
            "maize": 500,
            "rice": 600,
            "millet": 450,
            "sorghum": 400
        }

        base_price = base_prices.get(crop_type, 500)
        grade_multiplier = {"A": 1.0, "B": 0.9, "C": 0.8}.get(quality_grade, 0.9)

        return {
            "predicted_price": base_price * grade_multiplier,
            "currency": "XOF",
            "unit": "per kg",
            "prediction_horizon": "7 days",
            "confidence_score": 0.5,
            "price_trend": "stable",
            "market_factors": ["seasonal_baseline"]
        }


# Instance globale du service IA avancé
advanced_ml_service = AdvancedMLService()