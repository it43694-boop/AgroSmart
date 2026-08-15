"""Module 3: Micro-Insurance & Price Derivatives"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from services.kafka_service import publish_event, EventType
import random

logger = logging.getLogger(__name__)

class ParametricInsuranceService:
    """Assurance climat paramétrique (auto-indemnisation)"""

    @staticmethod
    def calculate_premium(farmer_id: int, crop_type: str, coverage_amount: float) -> Dict:
        """
        Calculer prime paramétrique basée sur:
        - Historique météo
        - Type culture
        - Localisation
        """
        # Tarification simple (en prod: modèle actuarial réel)
        base_rate = 0.08  # 8% du couvert

        risk_multipliers = {
            "tomato": 1.0,
            "rice": 1.3,  # Plus risky
            "millet": 0.9,
            "corn": 1.1
        }

        multiplier = risk_multipliers.get(crop_type, 1.0)
        premium = coverage_amount * base_rate * multiplier

        return {
            "farmer_id": farmer_id,
            "crop_type": crop_type,
            "coverage_amount": coverage_amount,
            "monthly_premium": round(premium / 12, 2),
            "triggers": {
                "rainfall_threshold": "< 50mm/month",
                "temperature": "> 40°C for 3+ days",
                "drought_index": "> 0.7"
            },
            "max_payout": coverage_amount * 0.8,
            "valid_until": (datetime.utcnow() + timedelta(days=365)).isoformat()
        }

    @staticmethod
    def trigger_claim(farmer_id: int, trigger_reason: str) -> Dict:
        """
        Auto-déclencher indemnisation si paramètre météo déclenche

        Utilise oracle (Chainlink) pour vérifier conditions
        """
        # Mock: vérifier si condition déclenchée
        weather_data = {
            "rainfall_mm": 40,  # < 50mm threshold
            "temperature_max": 42,  # > 40°C
            "drought_index": 0.75  # > 0.7
        }

        payout = 0
        claim_status = "pending"

        if weather_data["rainfall_mm"] < 50:
            payout = 200  # mock
            claim_status = "approved_auto"

        if claim_status == "approved_auto":
            publish_event(EventType.INSURANCE_TRIGGERED, {
                "farmer_id": farmer_id,
                "trigger_reason": trigger_reason,
                "payout_usd": payout,
                "timestamp": datetime.utcnow().isoformat()
            })

        logger.info(f"✓ Insurance claim triggered: {farmer_id} → ${payout}")

        return {
            "farmer_id": farmer_id,
            "claim_status": claim_status,
            "payout_usd": payout,
            "weather_data": weather_data
        }

class PriceDerivativesService:
    """Instruments de couverture prix (futures simplifié)"""

    @staticmethod
    def create_futures_contract(
        farmer_id: int,
        crop_type: str,
        quantity_kg: float,
        lock_price: float,
        settlement_month: int
    ) -> Dict:
        """
        Farmer lock prix aujourd'hui, acheter lock coût demain
        """
        try:
            contract = {
                "contract_id": f"FUT-{farmer_id}-{datetime.utcnow().timestamp()}",
                "seller": farmer_id,
                "crop_type": crop_type,
                "quantity_kg": quantity_kg,
                "locked_price": lock_price,
                "total_value": quantity_kg * lock_price,
                "settlement_month": settlement_month,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "expiry": (datetime.utcnow() + timedelta(days=settlement_month*30)).isoformat()
            }

            logger.info(f"✓ Futures contract created: {contract['contract_id']}")
            return contract

        except Exception as e:
            logger.error(f"✗ Futures creation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def find_buyer_hedges(contract: Dict) -> list:
        """
        Trouver buyers qui veulent hedger leurs coûts
        """
        try:
            # Mock buyers looking to hedge
            potential_buyers = [
                {
                    "buyer_id": 10,
                    "need_crop": contract["crop_type"],
                    "need_quantity": contract["quantity_kg"],
                    "budget": contract["total_value"] * 1.05,
                    "max_price": contract["locked_price"] * 1.08
                }
            ]

            matches = [b for b in potential_buyers if b["max_price"] >= contract["locked_price"]]
            return matches

        except Exception as e:
            logger.error(f"✗ Hedge matching failed: {e}")
            return []

    @staticmethod
    def settle_contract(contract_id: str, actual_price: float) -> Dict:
        """
        Règlement mensuel: comparaison prix réel vs locked
        """
        locked_price = 200  # mock
        settlement_payout = (actual_price - locked_price) * 100  # mock quantity

        return {
            "contract_id": contract_id,
            "locked_price": locked_price,
            "actual_price": actual_price,
            "settlement_payout": settlement_payout,
            "status": "settled",
            "timestamp": datetime.utcnow().isoformat()
        }

class CreditInsuranceService:
    """Assurance crédit pour acheteurs B2B"""

    @staticmethod
    def issue_buyer_protection(buyer_id: int, supplier_id: int, order_value: float) -> Dict:
        """
        Protéger buyer si supplier fait default
        """
        try:
            # Vérifier risque supplier (via AI score du Module 1)
            supplier_risk = "low"  # mock

            insurance_premium = order_value * 0.02 if supplier_risk == "low" else order_value * 0.05

            protection = {
                "protection_id": f"BUY-PROT-{buyer_id}-{supplier_id}",
                "buyer_id": buyer_id,
                "supplier_id": supplier_id,
                "order_value": order_value,
                "insurance_premium": insurance_premium,
                "coverage_percentage": 80,
                "max_claim": order_value * 0.8,
                "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "status": "active"
            }

            logger.info(f"✓ Buyer protection issued: {protection['protection_id']}")
            return protection

        except Exception as e:
            logger.error(f"✗ Credit insurance failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def file_claim(protection_id: str, reason: str) -> Dict:
        """
        Buyer déclare claim si supplier default
        """
        return {
            "protection_id": protection_id,
            "claim_status": "under_review",
            "reason": reason,
            "filed_at": datetime.utcnow().isoformat()
        }

# Service instances
parametric_insurance = ParametricInsuranceService()
price_derivatives = PriceDerivativesService()
credit_insurance = CreditInsuranceService()
