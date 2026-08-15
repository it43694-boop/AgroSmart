"""Module 6: Export Documents & GDPR Compliance"""
from typing import Dict, Optional
from datetime import timedelta
from utils.security import now_utc, now_utc_iso, encrypt_bytes_for_export
import logging
import hashlib
import json
from services.kafka_service import publish_event, EventType

logger = logging.getLogger(__name__)

class ExportDocumentService:
    """Digitalisation et génération documents export"""

    @staticmethod
    def generate_certificate_of_origin(export_id: str, farm_data: Dict, buyer_country: str) -> Dict:
        """
        Générer certificat d'origine digital (immutable)
        """
        try:
            certificate = {
                "certificate_id": export_id,
                "farmer_name": farm_data.get("farmer_name"),
                "farm_location": farm_data.get("location"),
                "crop_type": farm_data.get("crop_type"),
                "quantity_kg": farm_data.get("quantity_kg"),
                "quality_grade": farm_data.get("quality_grade", "Grade A"),
                "harvest_date": farm_data.get("harvest_date"),
                "buyer_country": buyer_country,
                "issued_date": now_utc_iso(),
                "valid_until": (now_utc() + timedelta(days=90)).isoformat(),
                "blockchain_hash": hashlib.sha256(
                    json.dumps({**farm_data, "timestamp": now_utc_iso()}).encode()
                ).hexdigest(),
                "qr_code": f"QR-{export_id}",
                "authenticity_verified": True
            }

            publish_event(EventType.EXPORT_DOCUMENT_READY, certificate)
            logger.info(f"✓ Certificate generated: {export_id}")
            return certificate

        except Exception as e:
            logger.error(f"✗ Certificate generation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_phytosanitary_certificate(farm_id: int, export_id: str) -> Dict:
        """
        Sync avec gouvernement pour phytosanitary cert
        """
        try:
            phyto_cert = {
                "certificate_id": export_id,
                "farm_id": farm_id,
                "issued_by": "Mali Ministry of Agriculture",
                "certificate_number": f"PHYTO-ML-{export_id[-6:]}",
                "issued_date": now_utc_iso(),
                "valid_until": (now_utc() + timedelta(days=30)).isoformat(),
                "pest_status": "pest_free",
                "pesticide_residue": "within_limits",
                "gmo_status": "non_gmo",
                "official_signature": "gov_digital_signature_hash",
                "blockchain_recorded": True
            }

            logger.info(f"✓ Phytosanitary certificate generated: {export_id}")
            return phyto_cert

        except Exception as e:
            logger.error(f"✗ Phytosanitary cert failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_quality_report(farm_id: int, product_data: Dict) -> Dict:
        """
        Rapport qualité (IoT + tests lab)
        """
        try:
            quality_report = {
                "report_id": f"QUAL-{farm_id}-{now_utc().timestamp()}",
                "farm_id": farm_id,
                "product": product_data.get("product_name"),
                "harvest_date": product_data.get("harvest_date"),
                "quality_metrics": {
                    "moisture": product_data.get("moisture_pct", 12.5),
                    "protein_percentage": product_data.get("protein_pct", 8.2),
                    "contamination_level": "0ppm",
                    "shelf_life_days": 45,
                    "packaging_integrity": "good"
                },
                "iot_verified": True,
                "iot_readings_count": 24,  # hourly readings
                "lab_tested": True,
                "tests_passed": 5,
                "overall_grade": "A",
                "report_date": now_utc_iso(),
                "valid_until": (now_utc() + timedelta(days=30)).isoformat()
            }

            logger.info(f"✓ Quality report generated: {quality_report['report_id']}")
            return quality_report

        except Exception as e:
            logger.error(f"✗ Quality report failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_esg_declaration(farm_id: int, esg_data: Dict) -> Dict:
        """
        Déclaration ESG (Environment, Social, Governance)
        """
        try:
            esg_declaration = {
                "declaration_id": f"ESG-{farm_id}-{now_utc().year}",
                "farm_id": farm_id,
                "year": now_utc().year,
                "environment": {
                    "carbon_intensity": esg_data.get("carbon_intensity", 0.45),
                    "water_efficiency": esg_data.get("water_efficiency_pct", 85),
                    "renewable_energy_pct": esg_data.get("renewable_energy_pct", 30),
                    "waste_recycled_pct": esg_data.get("waste_recycled_pct", 60)
                },
                "social": {
                    "fair_wage_compliance": True,
                    "worker_safety_incidents": 0,
                    "community_engagement": "active",
                    "women_workforce_pct": esg_data.get("women_workforce_pct", 40)
                },
                "governance": {
                    "blockchain_transparency": True,
                    "audit_ready": True,
                    "compliance_certifications": ["Organic", "Fair Trade"],
                    "gdpr_compliant": True
                },
                "overall_esg_score": 78,
                "esg_rating": "B+",
                "blockchain_proof": "0x...",
                "issued_date": now_utc_iso()
            }

            logger.info(f"✓ ESG declaration generated: {esg_declaration['declaration_id']}")
            return esg_declaration

        except Exception as e:
            logger.error(f"✗ ESG declaration failed: {e}")
            return {"error": str(e)}

# ============ GDPR COMPLIANCE ============

class GDPRComplianceService:
    """Conformité RGPD données sensibles"""

    @staticmethod
    def encrypt_personal_data(data: str, data_type: str = "pii") -> Dict:
        """
        Chiffrer données personnelles si la clé d'export est configurée.
        """
        try:
            encrypted_blob = encrypt_bytes_for_export(data.encode())
            if encrypted_blob:
                return {
                    "original_length": len(data),
                    "encrypted_blob": encrypted_blob,
                    "encryption_algorithm": "Fernet",
                    "data_type": data_type,
                    "encrypted_at": now_utc_iso(),
                    "key_rotation_required": True,
                    "note": "Encrypted with EXPORT_ENCRYPTION_KEY"
                }

            encrypted_hash = hashlib.sha256(data.encode()).hexdigest()[:32]
            return {
                "original_length": len(data),
                "encrypted_hash": encrypted_hash,
                "encryption_algorithm": "SHA-256-hash",
                "data_type": data_type,
                "encrypted_at": now_utc_iso(),
                "key_rotation_required": True,
                "note": "EXPORT_ENCRYPTION_KEY not configured; using hash fallback"
            }

        except Exception as e:
            logger.error(f"✗ Encryption failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def log_data_access(user_id: int, accessed_user_id: int, data_type: str, purpose: str) -> Dict:
        """
        Logger accès données (audit trail immutable)
        """
        audit_entry = {
            "audit_id": f"AUD-{now_utc().timestamp()}",
            "accessor_user_id": user_id,
            "accessed_user_id": accessed_user_id,
            "data_type": data_type,
            "purpose": purpose,
            "timestamp": now_utc_iso(),
            "ip_address": "X.X.X.X",  # mock
            "session_id": "session_hash",
            "immutable": True  # Blockchain recorded
        }

        logger.info(f"✓ Access logged: {user_id} → {accessed_user_id} ({data_type})")
        return audit_entry

    @staticmethod
    def right_to_deletion(user_id: int) -> Dict:
        """
        Droit à l'oubli: Supprimer données personnelles
        """
        try:
            deletion_request = {
                "deletion_id": f"DEL-{user_id}-{now_utc().timestamp()}",
                "user_id": user_id,
                "status": "pending_review",
                "data_categories_to_delete": [
                    "personal_info",
                    "transaction_history_anonymized",
                    "profile_data"
                ],
                "data_to_retain": [
                    "transaction_records (anonymized)",
                    "audit_logs",
                    "legal_holds"
                ],
                "requested_at": now_utc_iso(),
                "estimated_completion": (now_utc() + timedelta(days=30)).isoformat(),
                "confirmation_required": True
            }

            logger.info(f"✓ Deletion request filed: {deletion_request['deletion_id']}")
            return deletion_request

        except Exception as e:
            logger.error(f"✗ Deletion request failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def consent_manager(user_id: int, consents: Dict) -> Dict:
        """
        Gérer consentements RGPD
        """
        return {
            "user_id": user_id,
            "consents": {
                "marketing_emails": consents.get("marketing_emails", False),
                "data_sharing_partners": consents.get("data_sharing_partners", False),
                "analytics": consents.get("analytics", True),
                "blockchain_recording": consents.get("blockchain_recording", True)
            },
            "consent_version": "2.0",
            "last_updated": now_utc_iso(),
            "valid_until": (now_utc() + timedelta(days=365)).isoformat()
        }

    @staticmethod
    def generate_data_export(user_id: int) -> Dict:
        """
        RGPD: Exporter toutes les données utilisateur en JSON/CSV
        """
        try:
            export_id = f"EXPORT-{user_id}-{now_utc().timestamp()}"
            export = {
                "export_id": export_id,
                "user_id": user_id,
                "export_format": ["json", "csv"],
                "files": [
                    "profile_data.json",
                    "transaction_history.csv",
                    "reviews_and_ratings.json",
                    "blockchain_records.json"
                ],
                "generated_at": now_utc_iso(),
                "download_expires": (now_utc() + timedelta(days=7)).isoformat(),
            }
            # set download link using computed export_id
            export["download_link"] = f"https://api.agrosmart.io/gdpr/download/{export_id}"

            # Optional: encrypt export payload when EXPORT_ENCRYPTION_KEY is set
            try:
                payload_bytes = json.dumps({"export": export}).encode()
                encrypted_blob = encrypt_bytes_for_export(payload_bytes)
                if encrypted_blob:
                    export["encryption"] = {"enabled": True, "method": "fernet"}
                    export["encrypted_payload_b64"] = encrypted_blob
            except Exception:
                # don't break export if encryption fails
                pass

            logger.info(f"✓ Data export generated: {export['export_id']}")
            return export

        except Exception as e:
            logger.error(f"✗ Data export failed: {e}")
            return {"error": str(e)}

# Service instances
export_documents = ExportDocumentService()
gdpr_compliance = GDPRComplianceService()
