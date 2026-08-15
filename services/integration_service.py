"""Module 4: Intégrations Critiques - APIs, IoT, Wallets"""
from typing import Dict, Optional
from datetime import datetime
import logging
import os
from services.kafka_service import publish_event, EventType

logger = logging.getLogger(__name__)

# ============ BANKING INTEGRATIONS ============

class StripePaymentService:
    """Paiements instantanés via Stripe"""

    @staticmethod
    def process_payment(order_id: str, amount_usd: float, seller_id: int) -> Dict:
        """
        Créer et finaliser paiement Stripe
        """
        try:
            # Mock Stripe charge (en prod: vraie API)
            charge = {
                "id": f"ch_{order_id[:8]}",
                "amount": int(amount_usd * 100),  # cents
                "currency": "usd",
                "status": "succeeded" if amount_usd < 10000 else "requires_action",
                "created": datetime.utcnow().isoformat()
            }

            publish_event(EventType.PAYMENT_CONFIRMED, {
                "order_id": order_id,
                "seller_id": seller_id,
                "amount_usd": amount_usd,
                "stripe_charge_id": charge["id"]
            })

            logger.info(f"✓ Payment processed: {order_id} → ${amount_usd}")
            return charge

        except Exception as e:
            logger.error(f"✗ Stripe payment failed: {e}")
            return {"error": str(e)}

class MultiCurrencyService:
    """Multi-devise + SWIFT pour importateurs internationaux"""

    EXCHANGE_RATES = {
        "USD/EUR": 0.92,
        "USD/XOF": 600,  # West African Franc
        "USD/GBP": 0.79,
    }

    @staticmethod
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict:
        """Convertir devise"""
        rate_key = f"{from_currency}/{to_currency}"
        rate = MultiCurrencyService.EXCHANGE_RATES.get(rate_key, 1.0)

        return {
            "original_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": rate,
            "converted_amount": round(amount * rate, 2),
            "fee_percentage": 2.0,
            "final_amount": round(amount * rate * 0.98, 2)
        }

    @staticmethod
    def initiate_swift_transfer(
        buyer_country: str,
        seller_bank_account: str,
        amount_usd: float
    ) -> Dict:
        """
        SWIFT MT103 pour paiements internationaux B2B
        """
        try:
            swift_code = "BFCC" + buyer_country[:2]  # mock

            transfer = {
                "reference": f"SWIFT-{datetime.utcnow().timestamp()}",
                "sender_bank": "AgroBankMali",
                "sender_account": "AGRO-COLLECTIVE",
                "recipient_bank": buyer_country,
                "recipient_account": seller_bank_account,
                "amount_usd": amount_usd,
                "swift_code": swift_code,
                "status": "pending",
                "estimated_arrival": (datetime.utcnow().days + 2),
                "fees_usd": amount_usd * 0.01  # 1% fee
            }

            logger.info(f"✓ SWIFT transfer initiated: {transfer['reference']}")
            return transfer

        except Exception as e:
            logger.error(f"✗ SWIFT failed: {e}")
            return {"error": str(e)}

# ============ GOVERNMENT APIs ============

class GovernmentCertificationService:
    """Vérification et synchronisation certificats gouvernementaux"""

    @staticmethod
    def verify_agricultural_certificate(cert_number: str) -> Dict:
        """
        Vérifier certificat agricole auprès gouvernement Mali
        """
        try:
            # Mock gov API call
            is_valid = cert_number.startswith("CERT-")

            return {
                "certificate_number": cert_number,
                "is_valid": is_valid,
                "issued_date": "2024-05-01" if is_valid else None,
                "expiry_date": "2025-05-01" if is_valid else None,
                "farmer_name": "Farmer Smith" if is_valid else None,
                "crop_certified": "Tomato" if is_valid else None,
                "verified_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"✗ Certificate verification failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def sync_tax_registration(farmer_id: int, business_id: str) -> Dict:
        """
        Vérifier inscription fiscale
        """
        try:
            return {
                "farmer_id": farmer_id,
                "business_id": business_id,
                "tax_status": "compliant",
                "last_filing": "2024-03-15",
                "verified_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"✗ Tax sync failed: {e}")
            return {"error": str(e)}

# ============ IoT SENSOR INTEGRATION ============

class IoTSensorService:
    """Intégration capteurs IoT agricoles"""

    @staticmethod
    def ingest_sensor_data(farm_id: int, sensor_readings: Dict) -> Dict:
        """
        Recevoir données capteurs (température, humidité, GPS, etc.)
        """
        try:
            processed_data = {
                "farm_id": farm_id,
                "temperature_celsius": sensor_readings.get("temp", 28),
                "humidity_percentage": sensor_readings.get("humidity", 65),
                "soil_moisture": sensor_readings.get("soil_moisture", 0.45),
                "gps_location": sensor_readings.get("gps", {"lat": 12.65, "lon": -8.00}),
                "harvest_weight_kg": sensor_readings.get("weight", 100),
                "timestamp": datetime.utcnow().isoformat(),
                "data_valid": True
            }

            # Publier pour blockchain traceability
            publish_event(EventType.TRACEABILITY_RECORDED, processed_data)

            logger.info(f"✓ IoT data ingested: {farm_id}")
            return processed_data

        except Exception as e:
            logger.error(f"✗ IoT ingestion failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_farm_iot_status(farm_id: int) -> Dict:
        """
        Dashboard temps réel des capteurs
        """
        return {
            "farm_id": farm_id,
            "sensors_active": 4,
            "sensors_total": 5,
            "battery_level": 87,
            "last_sync": "2 minutes ago",
            "data_freshness": "green",
            "alerts": [
                {"level": "warning", "message": "Temperature above 35°C"}
            ]
        }

# ============ MOBILE WALLETS (light) ============

class MobileWalletService:
    """Wallets mobiles pour phones basiques (USSD + light apps)"""

    @staticmethod
    def generate_ussd_code(phone_number: str, action: str) -> Dict:
        """
        Code USSD pour transactions sur feature phones
        Ex: *123*1234# pour paiements
        """
        try:
            ussd_mapping = {
                "check_balance": "*123*0#",
                "send_money": "*123*1*{recipient}*{amount}#",
                "buy_credit": "*123*2*{amount}#",
                "check_wallet": "*123*3#"
            }

            ussd_code = ussd_mapping.get(action, "*123*#")

            return {
                "phone_number": phone_number,
                "ussd_code": ussd_code,
                "action": action,
                "instruction": f"Dial {ussd_code} to {action}",
                "sms_backup": f"SMS: {action.upper()} to 123"
            }

        except Exception as e:
            logger.error(f"✗ USSD generation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def register_offline_wallet(phone_number: str, farmer_name: str) -> Dict:
        """
        Créer wallet offline-first (local-first sync)
        """
        try:
            wallet = {
                "wallet_id": f"WAL-{phone_number[-8:]}",
                "phone_number": phone_number,
                "farmer_name": farmer_name,
                "balance": 0,
                "kyc_level": "basic",  # Phone + biometric only
                "created_at": datetime.utcnow().isoformat(),
                "sync_status": "ready",
                "offline_capable": True
            }

            logger.info(f"✓ Offline wallet created: {wallet['wallet_id']}")
            return wallet

        except Exception as e:
            logger.error(f"✗ Wallet registration failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def sync_offline_transactions(wallet_id: str, local_transactions: list) -> Dict:
        """
        Synchroniser transactions locales quand connection disponible
        """
        return {
            "wallet_id": wallet_id,
            "transactions_synced": len(local_transactions),
            "sync_status": "success",
            "sync_timestamp": datetime.utcnow().isoformat()
        }

# Service instances
stripe_payment = StripePaymentService()
multi_currency = MultiCurrencyService()
gov_certification = GovernmentCertificationService()
iot_sensors = IoTSensorService()
mobile_wallet = MobileWalletService()
