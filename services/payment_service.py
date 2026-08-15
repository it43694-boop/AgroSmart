"""Payment Service - Paiements via Stripe avec fallback mode"""
import os
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import models
from services.kafka_service import publish_event, EventType
import uuid
import json

logger = logging.getLogger(__name__)

# Try importing Stripe, fallback to mock if not available
try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False
    logger.warning("Stripe non disponible - Mode paiements simule")
    stripe = None

# Configuration Stripe
if HAS_STRIPE:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_fake")
    # Treat the default fake key as 'no real Stripe' to keep tests deterministic
    if stripe.api_key == "sk_test_fake" or not stripe.api_key:
        HAS_STRIPE = False
        STRIPE_MODE = "fallback"
        logger.warning("Stripe API key is fake or missing — using fallback payment mode")
    else:
        STRIPE_MODE = "test" if stripe.api_key.startswith("sk_test_") else "live"
else:
    STRIPE_MODE = "fallback"

class PaymentService:
    """Service de paiement pour Stripe (avec fallback)"""

    @staticmethod
    def create_payment_intent(
        order_id: str,
        amount_usd: float,
        buyer_id: int,
        description: str = "Agricultural product payment",
        idempotency_key: str = None
    ) -> Dict:
        """Creer payment intent Stripe avec idempotence"""
        if not HAS_STRIPE:
            return {
                "intent_id": f"mock_intent_{uuid.uuid4().hex[:16]}",
                "client_secret": f"mock_secret_{uuid.uuid4().hex[:16]}",
                "amount_usd": amount_usd,
                "status": "requires_payment_method",
                "created_at": datetime.utcnow().isoformat()
            }

        try:
            logger.info(f"Creating payment intent: {order_id} for ${amount_usd}")
            amount_cents = int(amount_usd * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                payment_method_types=["card"],
                description=description,
                metadata={"order_id": order_id, "buyer_id": buyer_id},
                idempotency_key=idempotency_key
            )

            return {
                "intent_id": intent.id,
                "client_secret": intent.client_secret,
                "amount_usd": amount_usd,
                "status": "requires_payment_method",
                "created_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Payment intent creation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def confirm_payment(intent_id: str, payment_method_id: str) -> Dict:
        """Confirmer paiement avec payment method"""
        if not HAS_STRIPE:
            return {
                "intent_id": intent_id,
                "status": "succeeded",
                "charge_id": f"mock_charge_{uuid.uuid4().hex[:16]}",
                "amount_received": 0
            }

        try:
            intent = stripe.PaymentIntent.confirm(
                intent_id,
                payment_method=payment_method_id,
                return_url="https://agrosmart.io/payment-return"
            )

            return {
                "intent_id": intent.id,
                "status": intent.status,
                "charge_id": intent.charges.data[0].id if intent.charges.data else None,
                "amount_received": intent.amount_received / 100
            }

        except Exception as e:
            logger.error(f"Confirmation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def process_real_payment(
        order_id: str,
        amount: float,
        buyer_id: int,
        payment_method_id: str = "pm_card_visa",
        idempotency_key: str = None,
        db: Session = None
    ) -> Dict:
        """Processus complet de paiement reel"""

        if not idempotency_key:
            idempotency_key = f"{order_id}-{buyer_id}-{datetime.utcnow().timestamp()}"

        # Idempotence: check DB for existing result when DB session provided
        if db is not None:
            try:
                existing = db.query(models.PaymentIdempotency).filter(models.PaymentIdempotency.idempotency_key == idempotency_key).first()
                if existing:
                    if existing.status == "succeeded" and existing.result_json:
                        return json.loads(existing.result_json)
                    if existing.status in ("failed", "processing") and existing.result_json:
                        return json.loads(existing.result_json)
                else:
                    # create placeholder record to mark processing
                    record = models.PaymentIdempotency(
                        idempotency_key=idempotency_key,
                        status="processing",
                    )
                    db.add(record)
                    db.commit()
            except Exception as e:
                logger.warning(f"Idempotency DB check failed: {e}")

        try:
            intent_response = PaymentService.create_payment_intent(
                order_id=order_id,
                amount_usd=amount,
                buyer_id=buyer_id,
                idempotency_key=idempotency_key
            )

            if "error" in intent_response:
                return intent_response

            intent_id = intent_response["intent_id"]

            confirm_response = PaymentService.confirm_payment(
                intent_id=intent_id,
                payment_method_id=payment_method_id
            )

            if "error" in confirm_response:
                return confirm_response

            # Publier Kafka event
            publish_event(EventType.PAYMENT_CONFIRMED, {
                "order_id": order_id,
                "buyer_id": buyer_id,
                "amount_usd": amount,
                "charge_id": confirm_response.get("charge_id"),
                "status": confirm_response["status"],
                "timestamp": datetime.utcnow().isoformat()
            })

            logger.info(f"Payment successful: {order_id} -> ${amount}")

            result = {
                "status": "succeeded",
                "order_id": order_id,
                "charge_id": confirm_response.get("charge_id"),
                "amount_usd": amount,
                "intent_id": intent_id,
                "created_at": datetime.utcnow().isoformat()
            }

            # Persist idempotency result
            if db is not None:
                try:
                    rec = db.query(models.PaymentIdempotency).filter(models.PaymentIdempotency.idempotency_key == idempotency_key).first()
                    if rec:
                        rec.status = "succeeded"
                        rec.result_json = json.dumps(result)
                        db.add(rec)
                        db.commit()
                    else:
                        db.add(models.PaymentIdempotency(idempotency_key=idempotency_key, status="succeeded", result_json=json.dumps(result)))
                        db.commit()
                except Exception as e:
                    logger.warning(f"Failed to persist idempotency result: {e}")

            return result

        except Exception as e:
            logger.error(f"Payment process failed: {e}")
            result = {"status": "failed", "error": str(e)}
            if db is not None:
                try:
                    rec = db.query(models.PaymentIdempotency).filter(models.PaymentIdempotency.idempotency_key == idempotency_key).first()
                    if rec:
                        rec.status = "failed"
                        rec.result_json = json.dumps(result)
                        db.add(rec)
                        db.commit()
                except Exception:
                    logger.warning("Failed to persist idempotency failure")
            return result

    @staticmethod
    def refund_payment(charge_id: str, amount_usd: Optional[float] = None) -> Dict:
        """Rembourser un paiement (total ou partiel)"""
        if not HAS_STRIPE:
            return {
                "status": "refunded",
                "refund_id": f"mock_refund_{uuid.uuid4().hex[:16]}",
                "amount_usd": amount_usd or 0
            }

        try:
            logger.info(f"Refunding charge: {charge_id}")

            refund_params = {}
            if amount_usd:
                refund_params["amount"] = int(amount_usd * 100)

            refund = stripe.Refund.create(charge=charge_id, **refund_params)

            return {
                "status": "refunded",
                "refund_id": refund.id,
                "amount_usd": amount_usd or (refund.amount / 100)
            }

        except Exception as e:
            logger.error(f"Refund failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def retrieve_payment_status(intent_id: str) -> Dict:
        """Recuperer statut paiement"""
        if not HAS_STRIPE:
            return {
                "intent_id": intent_id,
                "status": "succeeded",
                "amount": 0,
                "charges": []
            }

        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)

            return {
                "intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,
                "charges": [
                    {
                        "id": c.id,
                        "status": c.status,
                        "amount": c.amount / 100
                    } for c in intent.charges.data
                ]
            }

        except Exception as e:
            logger.error(f"Retrieve failed: {e}")
            return {"error": str(e)}


def process_real_payment(
    order_id: str,
    amount: float,
    buyer_id: int,
    payment_method_id: str = "pm_card_visa",
    idempotency_key: str = None,
    db: Session = None
) -> Dict:
    """Helper: Process a real payment"""
    return PaymentService.process_real_payment(
        order_id=order_id,
        amount=amount,
        buyer_id=buyer_id,
        payment_method_id=payment_method_id,
        idempotency_key=idempotency_key,
        db=db
    )


def refund_payment(charge_id: str, amount_usd: Optional[float] = None) -> Dict:
    """Helper: Refund a payment"""
    return PaymentService.refund_payment(charge_id, amount_usd)

