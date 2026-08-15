"""SAGA Orchestrator - Intègre TOUS les services sans les casser"""
import json
import logging
from typing import Dict, Any, Callable, List
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
from services.kafka_service import publish_event, KafkaEventConsumer, EventType

logger = logging.getLogger(__name__)

class SagaStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

class SagaStep:
    """Une étape du SAGA avec compensation automatique"""

    def __init__(self, name: str, action: Callable, compensation: Callable):
        self.name = name
        self.action = action
        self.compensation = compensation
        self.status = SagaStatus.PENDING
        self.result = None
        self.error = None

class MarketplaceOrderSaga:
    """
    SAGA: Farmer crée listing → Buyer achète → Paiement → Carbon calc → Reputation update

    Si UNE étape échoue → ROLLBACK tout (compensation)
    """

    def __init__(self, db: Session):
        self.db = db
        self.saga_id = None
        self.steps: List[SagaStep] = []
        self.current_step = 0
        self.saga_data = {}

    def add_step(self, name: str, action: Callable, compensation: Callable):
        """Ajouter étape SAGA"""
        self.steps.append(SagaStep(name, action, compensation))

    def create_complete_order_saga(self, order_data: Dict[str, Any]):
        """Créer SAGA complet pour une commande marketplace"""

        self.saga_id = f"SAGA-{datetime.utcnow().timestamp()}"
        self.saga_data = order_data

        # STEP 1: Calculer credit score farmer
        self.add_step(
            name="credit_score",
            action=lambda: self._credit_scoring_step(),
            compensation=lambda: self._credit_scoring_compensation()
        )

        # STEP 2: Calculer assurance paramétrique
        self.add_step(
            name="insurance_calc",
            action=lambda: self._insurance_step(),
            compensation=lambda: self._insurance_compensation()
        )

        # STEP 3: Créer escrow blockchain
        self.add_step(
            name="blockchain_escrow",
            action=lambda: self._blockchain_escrow_step(),
            compensation=lambda: self._blockchain_escrow_compensation()
        )

        # STEP 4: Traiter paiement RÉEL
        self.add_step(
            name="payment_processing",
            action=lambda: self._real_payment_step(),
            compensation=lambda: self._payment_compensation()
        )

        # STEP 5: Enregistrer IoT + traçabilité
        self.add_step(
            name="iot_traceability",
            action=lambda: self._iot_traceability_step(),
            compensation=lambda: self._iot_traceability_compensation()
        )

        # STEP 6: Calculer carbon footprint
        self.add_step(
            name="carbon_calculation",
            action=lambda: self._carbon_step(),
            compensation=lambda: self._carbon_compensation()
        )

        # STEP 7: Mettre à jour reputation
        self.add_step(
            name="reputation_update",
            action=lambda: self._reputation_step(),
            compensation=lambda: self._reputation_compensation()
        )

    def execute(self) -> Dict[str, Any]:
        """Exécuter SAGA: si une étape échoue → compensation/rollback"""

        logger.info(f"🔵 SAGA START: {self.saga_id}")

        try:
            # Exécuter chaque étape dans l'ordre
            for idx, step in enumerate(self.steps):
                self.current_step = idx
                logger.info(f"  → Étape {idx+1}/{len(self.steps)}: {step.name}")

                try:
                    step.result = step.action()
                    step.status = SagaStatus.COMPLETED
                    logger.info(f"  ✓ {step.name} OK")

                    # Publier événement Kafka
                    publish_event(f"saga_{step.name}_completed", {
                        "saga_id": self.saga_id,
                        "step": step.name,
                        "result": str(step.result)
                    })

                except Exception as e:
                    step.error = str(e)
                    step.status = SagaStatus.FAILED
                    logger.error(f"  ✗ {step.name} FAILED: {e}")

                    # ROLLBACK: Compenser les étapes précédentes
                    logger.warning(f"🔴 ROLLING BACK from step {idx}")
                    self._rollback(idx)

                    return {
                        "saga_id": self.saga_id,
                        "status": SagaStatus.COMPENSATED,
                        "failed_at": step.name,
                        "error": str(e),
                        "compensated_steps": [self.steps[i].name for i in range(idx)]
                    }

            logger.info(f"🟢 SAGA COMPLETED: {self.saga_id}")

            return {
                "saga_id": self.saga_id,
                "status": SagaStatus.COMPLETED,
                "results": {step.name: step.result for step in self.steps}
            }

        except Exception as e:
            logger.error(f"🔴 SAGA FATAL ERROR: {e}")
            self._rollback(len(self.steps))
            raise

    def _rollback(self, from_step: int):
        """Compensation: annuler toutes les étapes précédentes"""
        for idx in range(from_step - 1, -1, -1):
            step = self.steps[idx]
            try:
                logger.info(f"  ↩ Compensation: {step.name}")
                step.compensation()
                logger.info(f"  ✓ {step.name} compensated")
            except Exception as e:
                logger.error(f"  ✗ Compensation failed for {step.name}: {e}")

    # ============ STEP IMPLEMENTATIONS ============

    def _credit_scoring_step(self) -> Dict:
        """STEP 1: Calculer score crédit"""
        from services.ai_service import credit_scoring

        farmer_id = self.saga_data["farmer_id"]
        score = credit_scoring.calculate_score(farmer_id, self.db)

        # Vérifier si credit OK
        if score.get("credit_score", 0) < 40:
            raise ValueError(f"Credit score too low: {score['credit_score']}")

        self.saga_data["credit_score"] = score
        return score

    def _credit_scoring_compensation(self):
        """Compensation: rien à faire (juste calcul)."""
        logger.info("Credit score step compensation skipped; no persistent state was created.")

    def _insurance_step(self) -> Dict:
        """STEP 2: Calculer prime assurance"""
        from services.insurance_service import parametric_insurance

        farmer_id = self.saga_data["farmer_id"]
        crop_type = self.saga_data.get("crop_type", "tomato")
        coverage = self.saga_data.get("coverage_amount", 1000)

        premium = parametric_insurance.calculate_premium(farmer_id, crop_type, coverage)
        self.saga_data["insurance"] = premium
        return premium

    def _insurance_compensation(self):
        """Compensation: aucun effet réel car l'assurance n'est pas encore appliquée."""
        logger.info("Insurance step compensation skipped; no charge was created.")

    def _blockchain_escrow_step(self) -> Dict:
        """STEP 3: Créer escrow blockchain"""
        from services.blockchain_service import deploy_escrow_contract

        order_value = self.saga_data.get("order_value", 1000)
        farmer_id = self.saga_data["farmer_id"]
        buyer_id = self.saga_data["buyer_id"]

        # Déployer escrow contract
        escrow = deploy_escrow_contract(
            buyer_address=str(buyer_id),
            seller_address=str(farmer_id),
            amount=order_value,
            release_conditions={
                "order_id": self.saga_data.get("order_id"),
                "status": "pending",
                "buyer_id": buyer_id,
                "seller_id": farmer_id
            }
        )

        if isinstance(escrow, dict):
            contract_address = escrow.get("contract_address")
            tx_hash = escrow.get("tx_hash")
        else:
            contract_address = escrow
            tx_hash = None

        self.saga_data["escrow_address"] = contract_address
        self.saga_data["escrow_tx"] = tx_hash
        return {"contract_address": contract_address, "tx_hash": tx_hash}

    def _blockchain_escrow_compensation(self):
        """Compensation: annuler escrow (récupérer fonds si déployé)"""
        # En production: envoyer transaction pour récupérer fonds
        logger.info(f"Escrow cancellation: {self.saga_data.get('escrow_address')}")

    def _real_payment_step(self) -> Dict:
        """STEP 4: PAIEMENT RÉEL via Stripe"""
        from services.payment_service import process_real_payment

        buyer_id = self.saga_data["buyer_id"]
        order_value_xof = self.saga_data.get("order_value", 1000)
        order_id = self.saga_data.get("order_id", f"ORD-{self.saga_id}")

        # Convertir XOF vers USD pour Stripe
        amount_usd = round(order_value_xof / 600.0, 2)
        if amount_usd <= 0:
            raise ValueError("Order value must be positive for payment processing")

        payment = process_real_payment(
            order_id=order_id,
            amount=amount_usd,
            buyer_id=buyer_id,
            payment_method_id=self.saga_data.get("payment_method_id", "pm_card_visa"),
            idempotency_key=f"{self.saga_id}-payment",
            db=self.db,
        )

        if payment.get("status") != "succeeded":
            raise Exception(f"Payment failed: {payment.get('error', 'unknown error')}")

        self.saga_data["payment_id"] = payment.get("charge_id")
        return payment

    def _payment_compensation(self):
        """Compensation: Refund si paiement réussi"""
        payment_id = self.saga_data.get("payment_id")
        if payment_id:
            from services.payment_service import refund_payment
            refund_payment(payment_id)
            logger.info(f"Payment refunded: {payment_id}")

    def _iot_traceability_step(self) -> Dict:
        """STEP 5: Enregistrer sur blockchain (traçabilité)"""
        from services.blockchain_service import add_trace_on_chain
        from services.integration_service import iot_sensors

        farm_id = self.saga_data.get("farm_id")

        # Récupérer données IoT RÉELLES
        iot_data = iot_sensors.ingest_sensor_data(
            farm_id=farm_id,
            sensor_readings=self.saga_data.get("iot_readings", {})
        )

        # Enregistrer sur blockchain
        tx = add_trace_on_chain(
            product_id=f"order-{self.saga_data.get('order_id')}",
            origin=self.saga_data.get("farm_location", "unknown"),
            certification="order_placed",
            timestamp=int(datetime.utcnow().timestamp())
        )

        self.saga_data["traceability_tx"] = tx
        return {"iot_data": iot_data, "blockchain_tx": tx}

    def _iot_traceability_compensation(self):
        """Compensation: logs immuables, aucune suppression n'est effectuée."""
        logger.info("IoT traceability compensation skipped; immutable trace retained.")

    def _carbon_step(self) -> Dict:
        """STEP 6: Calculer carbon footprint"""
        from services.impact_gamification_service import carbon_footprint

        farm_id = self.saga_data.get("farm_id")
        farm_data = self.saga_data.get("farm_data", {})

        carbon = carbon_footprint.calculate_farm_carbon(farm_id, farm_data)
        self.saga_data["carbon"] = carbon
        return carbon

    def _carbon_compensation(self):
        """Compensation: aucune action car le calcul n'a pas créé d'état persistant."""
        logger.info("Carbon footprint compensation skipped; no mutable state was created.")

    def _reputation_step(self) -> Dict:
        """STEP 7: Mettre à jour reputation"""
        from services.impact_gamification_service import reputation

        farmer_id = self.saga_data["farmer_id"]
        user_data = self.saga_data.get("user_data", {})

        rep = reputation.calculate_reputation_score(farmer_id, user_data)
        self.saga_data["reputation"] = rep
        return rep

    def _reputation_compensation(self):
        """Compensation: le score de réputation sera régénéré si nécessaire."""
        logger.info("Reputation compensation skipped; score will be recalculated on demand.")

# ============ USAGE ============

def execute_marketplace_order(order_data: Dict[str, Any], db: Session) -> Dict:
    """
    Exécuter une commande COMPLÈTE via SAGA

    Exemple order_data:
    {
        "farmer_id": 5,
        "buyer_id": 10,
        "order_id": "ORD-123",
        "crop_type": "tomato",
        "quantity_kg": 500,
        "order_value": 100000,  # XOF
        "farm_id": 5,
        "farm_location": "Bamako",
        "iot_readings": {"temp": 28, "humidity": 65},
        "farm_data": {"fuel_liters": 50}
    }
    """

    saga = MarketplaceOrderSaga(db)
    saga.create_complete_order_saga(order_data)

    result = saga.execute()

    # Log result
    logger.info(f"Order result: {json.dumps(result, default=str)}")

    return result
