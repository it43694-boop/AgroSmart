"""Routers - Endpoints FastAPI pour tous les modules"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from services.ai_service import credit_scoring, yield_prediction, fraud_detection, matching_engine
from services.insurance_service import parametric_insurance, price_derivatives, credit_insurance
from services.integration_service import stripe_payment, multi_currency, gov_certification, iot_sensors, mobile_wallet
from services.impact_gamification_service import carbon_footprint, reputation, gamification
from services.export_compliance_service import export_documents, gdpr_compliance
from services.dao_governance_service import dao_governance, treasury, community_pool
from database import SessionLocal
import auth
import models
import logging

logger = logging.getLogger(__name__)

# ============ ROUTERS ============

ai_router = APIRouter(prefix="/api/ai", tags=["AI & Analytics"])
insurance_router = APIRouter(prefix="/api/insurance", tags=["Insurance"])
integration_router = APIRouter(prefix="/api/integrations", tags=["Integrations"])
impact_router = APIRouter(prefix="/api/impact", tags=["Impact & Gamification"])
compliance_router = APIRouter(prefix="/api/compliance", tags=["Export & Compliance"])
dao_router = APIRouter(prefix="/api/dao", tags=["DAO Governance"])

# ============ MODULE 1: AI & ANALYTICS ============

@ai_router.post("/credit-score")
def compute_credit_score(farmer_id: int):
    """Calculer score crédit pour farmer"""
    return credit_scoring.calculate_score(farmer_id, SessionLocal())

@ai_router.post("/yield-prediction")
def predict_crop_yield(farmer_id: int, crop_type: str):
    """Prédire rendement récolte"""
    return yield_prediction.predict_yield(farmer_id, crop_type, SessionLocal())

@ai_router.post("/fraud-detection")
def check_fraud(payload: dict):
    """Détecter fraude en temps réel (attend JSON body)"""
    transaction_id = payload.get("transaction_id")
    transaction_data = payload.get("transaction_data") or payload
    is_fraud, risk_level, score = fraud_detection.detect_fraud(transaction_id, transaction_data)
    return {
        "transaction_id": transaction_id,
        "is_fraud": is_fraud,
        "risk_level": risk_level,
        "anomaly_score": score
    }

@ai_router.get("/matching/{farmer_id}")
def find_buyer_matches(farmer_id: int, crop_type: str):
    """Trouver buyers pour farmer"""
    return matching_engine.find_matches(farmer_id, crop_type, SessionLocal())

# ============ MODULE 3: INSURANCE ============

@insurance_router.post("/premium")
def calculate_insurance_premium(farmer_id: int, crop_type: str, coverage_amount: float):
    """Calculer prime paramétrique"""
    return parametric_insurance.calculate_premium(farmer_id, crop_type, coverage_amount)

@insurance_router.post("/claim")
def trigger_insurance_claim(farmer_id: int, trigger_reason: str):
    """Déclencher indemnisation auto"""
    return parametric_insurance.trigger_claim(farmer_id, trigger_reason)

@insurance_router.post("/futures-contract")
def create_futures(payload: dict):
    """Créer contrat futures prix (attend JSON body)"""
    return price_derivatives.create_futures_contract(
        payload.get("farmer_id"),
        payload.get("crop_type"),
        payload.get("quantity_kg"),
        payload.get("lock_price"),
        payload.get("settlement_month"),
    )

@insurance_router.post("/buyer-protection")
def issue_buyer_insurance(payload: dict):
    """Assurer acheteur contre default supplier (attend JSON body)"""
    return credit_insurance.issue_buyer_protection(
        payload.get("buyer_id"),
        payload.get("supplier_id"),
        payload.get("order_value"),
    )

# ============ MODULE 4: INTEGRATIONS ============

@integration_router.post("/payment/stripe")
def process_stripe_payment(payload: dict):
    """Paiement Stripe instantané (attend JSON body)"""
    return stripe_payment.process_payment(
        payload.get("order_id"),
        payload.get("amount_usd"),
        payload.get("seller_id"),
    )

@integration_router.get("/currency/convert")
def convert_currencies(amount: float, from_currency: str, to_currency: str):
    """Convertir devises avec rates actueiles"""
    return multi_currency.convert_currency(amount, from_currency, to_currency)

@integration_router.post("/payment/swift")
def initiate_swift(buyer_country: str, seller_bank_account: str, amount_usd: float):
    """Paiement international SWIFT"""
    return multi_currency.initiate_swift_transfer(buyer_country, seller_bank_account, amount_usd)

@integration_router.get("/certification/verify")
def verify_certification(cert_number: str):
    """Vérifier certificat gouvernement"""
    return gov_certification.verify_agricultural_certificate(cert_number)

@integration_router.post("/iot/sensor-data")
def ingest_iot_data(payload: dict):
    """Ingérer données capteurs IoT (attend JSON body)"""
    return iot_sensors.ingest_sensor_data(payload.get("farm_id"), payload.get("sensor_readings", {}))

@integration_router.get("/iot/farm-status/{farm_id}")
def get_farm_iot_status(farm_id: int):
    """Dashboard IoT farm"""
    return iot_sensors.get_farm_iot_status(farm_id)

@integration_router.post("/wallet/ussd")
def generate_ussd(payload: dict):
    """Code USSD pour feature phones (attend JSON body)"""
    return mobile_wallet.generate_ussd_code(payload.get("phone_number"), payload.get("action"))

@integration_router.post("/wallet/register-offline")
def register_offline_wallet(phone_number: str, farmer_name: str):
    """Créer wallet offline-first"""
    return mobile_wallet.register_offline_wallet(phone_number, farmer_name)

# ============ MODULE 5: IMPACT & GAMIFICATION ============

@impact_router.post("/carbon/calculate")
def calculate_carbon(payload: dict):
    """Calculer carbon footprint (attend JSON body)"""
    return carbon_footprint.calculate_farm_carbon(payload.get("farm_id"), payload.get("farm_data", {}))

@impact_router.post("/carbon/mint-nft")
def mint_carbon_nft(payload: dict):
    """Créer NFT crédits carbones (attend JSON body)"""
    return carbon_footprint.mint_carbon_credits_nft(payload.get("farm_id"), payload.get("tonnes_offset"))

@impact_router.post("/reputation/calculate")
def calculate_reputation(payload: dict):
    """Calculer reputation score (attend JSON body)"""
    return reputation.calculate_reputation_score(payload.get("user_id"), payload.get("user_data", {}))

@impact_router.post("/badges/award")
def award_badge(payload: dict):
    """Attribuer badge (attend JSON body)"""
    return gamification.award_badge(payload.get("user_id"), payload.get("badge_key"))

@impact_router.get("/leaderboard")
def get_leaderboard(timeframe: str = Query("monthly")):
    """Leaderboard farmers"""
    return gamification.get_leaderboard(timeframe)

@impact_router.post("/rewards/distribute")
def distribute_rewards(timeframe: str):
    """Distribuer récompenses"""
    return gamification.distribute_rewards(timeframe)

# ============ MODULE 6: EXPORT & COMPLIANCE ============

@compliance_router.post("/certificate/origin")
def generate_origin_cert(payload: dict):
    """Certificat d'origine (attend JSON body)"""
    return export_documents.generate_certificate_of_origin(
        payload.get("export_id"),
        payload.get("farm_data", {}),
        payload.get("buyer_country"),
    )

@compliance_router.post("/certificate/phytosanitary")
def generate_phyto_cert(farm_id: int, export_id: str):
    """Phytosanitary certificate"""
    return export_documents.generate_phytosanitary_certificate(farm_id, export_id)

@compliance_router.post("/report/quality")
def generate_quality_report(farm_id: int, product_data: dict):
    """Rapport qualité"""
    return export_documents.generate_quality_report(farm_id, product_data)

@compliance_router.post("/declaration/esg")
def generate_esg_declaration(farm_id: int, esg_data: dict):
    """Déclaration ESG"""
    return export_documents.generate_esg_declaration(farm_id, esg_data)

@compliance_router.post("/gdpr/data-export")
def export_user_data(current_user: models.User = Depends(auth.get_current_user), user_id: int = None, payload: dict = None):
    """RGPD: Exporter données utilisateur. Supporte query `user_id` ou JSON body {"user_id": N}"""
    uid = user_id or (payload and payload.get("user_id")) or current_user.id
    return gdpr_compliance.generate_data_export(uid)

@compliance_router.post("/gdpr/right-to-deletion")
def request_deletion(current_user: models.User = Depends(auth.get_current_user), user_id: int = None, payload: dict = None):
    """RGPD: Droit à l'oubli. Supporte query `user_id` ou JSON body {"user_id": N}"""
    uid = user_id or (payload and payload.get("user_id")) or current_user.id
    return gdpr_compliance.right_to_deletion(uid)

@compliance_router.get("/gdpr/audit-log")
def get_audit_log(current_user: models.User = Depends(auth.get_current_user), user_id: int = Query(...), accessed_user_id: int = Query(None), data_type: str = Query("personal_info"), purpose: str = Query("audit")):
    """Voir audit log d'accès données"""
    if accessed_user_id is None:
        return {
            "message": "Audit log retrieved",
            "user_id": user_id,
            "note": "Pass accessed_user_id to produce a logged access entry"
        }
    return gdpr_compliance.log_data_access(user_id, accessed_user_id, data_type, purpose)


@compliance_router.post("/gdpr/consent")
def manage_gdpr_consent(current_user: models.User = Depends(auth.get_current_user), payload: dict = None):
    """Enregistrer ou mettre à jour un consentement RGPD"""
    user_id = (payload and payload.get("user_id")) or current_user.id
    return gdpr_compliance.consent_manager(
        user_id,
        payload.get("consents", {}),
    )

# ============ MODULE 7: DAO ============

@dao_router.post("/proposal/create")
def create_proposal(payload: dict):
    """Créer proposition DAO (attend JSON body)"""
    return dao_governance.create_proposal(
        payload.get("proposer_id"),
        payload.get("title"),
        payload.get("description"),
        payload.get("proposal_type"),
        payload.get("funding_requested_usd"),
    )

@dao_router.post("/proposal/vote")
def cast_dao_vote(payload: dict):
    """Voter sur proposition (attend JSON body)"""
    return dao_governance.cast_vote(
        payload.get("voter_id"),
        payload.get("proposal_id"),
        payload.get("vote_choice"),
        payload.get("voting_power"),
    )

@dao_router.get("/treasury/balance")
def get_treasury():
    """Solde trésor DAO"""
    return treasury.get_treasury_balance()

@dao_router.post("/funds/distribute")
def request_fund_distribution(recipient_id: int, amount_usd: float, purpose: str, proposal_id: str):
    """Demander distribution fonds"""
    return treasury.request_fund_distribution(recipient_id, amount_usd, purpose, proposal_id)

@dao_router.post("/pool/create")
def create_insurance_pool(payload: dict):
    """Créer pool assurance mutualisée (attend JSON body)"""
    return community_pool.create_insurance_pool(
        payload.get("pool_name"),
        payload.get("pool_type"),
        payload.get("min_members"),
    )

@dao_router.post("/pool/join")
def join_insurance_pool(pool_id: str, member_id: int, contribution_usd: float):
    """Rejoindre pool"""
    return community_pool.join_pool(pool_id, member_id, contribution_usd)

# ============ EXPORT ROUTERS ============

__all__ = [
    "ai_router",
    "insurance_router",
    "integration_router",
    "impact_router",
    "compliance_router",
    "dao_router"
]
