"""Module 1: AI & Analytics - Credit Scoring, Yield Prediction, Fraud Detection"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from services.kafka_service import publish_event, EventType
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CreditScoringService:
    """Scoring crédit pour petits producteurs sans historique"""

    @staticmethod
    def calculate_score(farmer_id: int, db: Session) -> Dict:
        """
        Scoring alternatif (sans historique bancaire):
        - Données IoT (capteurs agriculture)
        - Historique paiements marketplace
        - Données comportementales (phone)
        - Score social (réseau)
        """
        try:
            # Récupérer données farmer
            farmer_data = {
                "farmer_id": farmer_id,
                "phone_history": 30,  # # jours activité phone
                "iot_compliance": 85,  # % capteurs bien utilisés
                "payment_history": 95,  # % paiements à temps
                "group_reputation": 4.5,  # /5 du groupe agricole
                "land_area": 2.5,  # hectares
            }

            # Algorithme alternatif: weighted scoring
            score = (
                farmer_data["phone_history"] * 0.15 +
                farmer_data["iot_compliance"] * 0.25 +
                farmer_data["payment_history"] * 0.30 +
                farmer_data["group_reputation"] * 18 +  # /5 → /90
                min(farmer_data["land_area"] * 10, 100) * 0.15
            ) / 100 * 100

            risk_level = "low" if score >= 75 else "medium" if score >= 50 else "high"

            result = {
                "farmer_id": farmer_id,
                "credit_score": round(score, 2),
                "risk_level": risk_level,
                "recommended_credit_limit": 500 if score >= 75 else 250,  # USD
                "interest_rate": 8 if score >= 75 else 15,  # %
                "timestamp": datetime.utcnow().isoformat()
            }

            # Publier event
            publish_event(EventType.CREDIT_SCORE_COMPUTED, result)

            logger.info(f"✓ Credit score computed: {farmer_id} → {score}")
            return result

        except Exception as e:
            logger.error(f"✗ Credit scoring failed: {e}")
            return {"error": str(e)}

class YieldPredictionService:
    """Prédiction rendements récoltes"""

    @staticmethod
    def predict_yield(farmer_id: int, crop_type: str, db: Session) -> Dict:
        """
        Prédire rendement basé sur:
        - Historique farmer
        - Données météo
        - Qualité sol
        - Saisonnalité
        """
        try:
            # Mock data (en prod: vraie donnée météo + IoT)
            features = {
                "previous_yield": 800,  # kg
                "rainfall_seasonal": 450,  # mm
                "temperature_avg": 28,  # °C
                "soil_quality": 7.2,  # /10
                "fertilizer_usage": 150,  # kg/ha
            }

            # Simple LSTM-like prediction (mock)
            base_yield = features["previous_yield"]
            rain_factor = features["rainfall_seasonal"] / 400  # normalized
            temp_factor = 1.0 if 25 <= features["temperature_avg"] <= 32 else 0.8
            soil_factor = features["soil_quality"] / 10
            fertilizer_factor = min(features["fertilizer_usage"] / 200, 1.2)

            predicted_yield = base_yield * rain_factor * temp_factor * soil_factor * fertilizer_factor

            result = {
                "farmer_id": farmer_id,
                "crop_type": crop_type,
                "predicted_yield_kg": round(predicted_yield, 2),
                "confidence": 0.82,
                "risk_factors": ["dry_season", "market_volatility"],
                "recommendations": [
                    "Augmenter irrigation si pluies faibles",
                    "Vérifier Ph sol"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }

            publish_event(EventType.YIELD_PREDICTION_READY, result)
            logger.info(f"✓ Yield predicted: {farmer_id} → {predicted_yield}kg")
            return result

        except Exception as e:
            logger.error(f"✗ Yield prediction failed: {e}")
            return {"error": str(e)}

class FraudDetectionService:
    """Détection fraude en temps réel"""

    @staticmethod
    def detect_fraud(transaction_id: str, transaction_data: Dict) -> Tuple[bool, str, float]:
        """
        Détecter fraude:
        - Double spending escrow
        - Pattern anomalies
        - Identity verification
        """
        anomaly_score = 0.0
        red_flags = []

        # Rule 1: Double spend detection
        if transaction_data.get("escrow_amount", 0) > 1000:
            anomaly_score += 0.2
            red_flags.append("High escrow amount")

        # Rule 2: Velocity check (# transactions dans last hour)
        if transaction_data.get("seller_transactions_last_hour", 0) > 5:
            anomaly_score += 0.3
            red_flags.append("High transaction velocity")

        # Rule 3: Identity check (phone verification)
        if not transaction_data.get("buyer_phone_verified", False):
            anomaly_score += 0.25
            red_flags.append("Phone not verified")

        # Rule 4: First time buyer
        if transaction_data.get("buyer_transaction_count", 0) == 0:
            anomaly_score += 0.15
            red_flags.append("First-time buyer")

        is_fraud = anomaly_score > 0.6
        risk_level = "high" if is_fraud else "medium" if anomaly_score > 0.3 else "low"

        if is_fraud:
            publish_event(EventType.FRAUD_ALERT, {
                "transaction_id": transaction_id,
                "anomaly_score": anomaly_score,
                "red_flags": red_flags,
                "action": "BLOCK"
            })
            logger.warning(f"⚠ Fraud detected: {transaction_id}")

        return is_fraud, risk_level, anomaly_score

class MatchingEngineService:
    """Matching automatique acheteur/vendeur"""

    @staticmethod
    def find_matches(farmer_id: int, crop_type: str, db: Session) -> list:
        """
        Trouver meilleurs buyers basé sur:
        - Besoin acheteur
        - Prix agriculteur
        - Localisation
        - Historique trading
        """
        try:
            # Mock buyers (en prod: query DB)
            buyers = [
                {
                    "buyer_id": 1,
                    "need": "tomato",
                    "quantity_needed": 500,
                    "location": "Bamako",
                    "reputation": 4.8,
                    "avg_price": 200
                },
                {
                    "buyer_id": 2,
                    "need": "tomato",
                    "quantity_needed": 300,
                    "location": "Koulikoro",
                    "reputation": 4.2,
                    "avg_price": 180
                }
            ]

            matches = []
            for buyer in buyers:
                if buyer["need"] == crop_type:
                    # Score similarity
                    similarity = (
                        (buyer["reputation"] / 5) * 0.4 +  # Quality
                        (1 - abs(buyer["avg_price"] - 200) / 200) * 0.6  # Price fit
                    )

                    if similarity > 0.5:
                        matches.append({
                            "buyer_id": buyer["buyer_id"],
                            "score": round(similarity * 100, 2),
                            "potential_price": buyer["avg_price"],
                            "distance_km": 50,  # mock
                        })

            matches = sorted(matches, key=lambda x: x["score"], reverse=True)
            logger.info(f"✓ Matches found for farmer {farmer_id}: {len(matches)}")
            return matches

        except Exception as e:
            logger.error(f"✗ Matching failed: {e}")
            return []

# Service instances
credit_scoring = CreditScoringService()
yield_prediction = YieldPredictionService()
fraud_detection = FraudDetectionService()
matching_engine = MatchingEngineService()
