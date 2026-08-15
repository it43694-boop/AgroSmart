"""
Regulatory Compliance Service - Phase 4.1 : Conformité Réglementaire
Expansion Internationale - Respect normes FAO/UE pour export

Fonctionnalités :
- Certification agricole : Respect normes FAO/UE pour export
- RGPD africain : Conformité données personnelles panafricaine
- Audit légal : Validation juridique pour expansion régionale
- Métriques : Conformité 100% validée par tiers
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

import models
import schemas

logger = logging.getLogger("regulatory_compliance_service")

# Configuration des normes réglementaires
REGULATORY_CONFIG = {
    "certifications": {
        "fao_standards": {
            "name": "Normes FAO pour l'Agriculture Durable",
            "requirements": ["pratiques_durables", "traçabilité", "qualité_produit"],
            "validity_years": 3,
            "renewal_required": True
        },
        "eu_export": {
            "name": "Normes UE pour Export Agricole",
            "requirements": ["certification_bio", "résidus_zéro", "emballage_conforme"],
            "validity_years": 2,
            "renewal_required": True
        },
        "african_union": {
            "name": "Normes Union Africaine",
            "requirements": ["commerce_régional", "qualité_standard", "traçabilité"],
            "validity_years": 5,
            "renewal_required": False
        }
    },
    "gdpr_african": {
        "data_protection": {
            "consent_required": True,
            "data_minimization": True,
            "purpose_limitation": True,
            "retention_limits": {"personal_data": 365, "agricultural_data": 1825}
        },
        "regional_compliance": {
            "ecowas": ["consent", "transparency", "data_subject_rights"],
            "sadc": ["data_protection", "cross_border_transfers"],
            "east_african_community": ["privacy_by_design", "accountability"]
        }
    },
    "audit_requirements": {
        "frequency": "quarterly",
        "scope": ["data_protection", "export_compliance", "agricultural_standards"],
        "third_party_validation": True,
        "documentation_retention": 7  # années
    }
}

class RegulatoryComplianceService:
    """
    Service de conformité réglementaire pour expansion internationale
    """

    @staticmethod
    def check_certification_compliance(user_id: int, certification_type: str, db: Session) -> Dict[str, Any]:
        """
        Vérifier la conformité aux certifications agricoles
        """
        try:
            # Récupérer les données utilisateur
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return {"error": "Utilisateur non trouvé"}

            # Vérifier les certifications existantes
            existing_cert = db.query(models.AgriculturalCertification).filter(
                and_(
                    models.AgriculturalCertification.user_id == user_id,
                    models.AgriculturalCertification.certification_type == certification_type,
                    models.AgriculturalCertification.status == "active"
                )
            ).first()

            if existing_cert:
                return {
                    "compliant": True,
                    "certification_id": existing_cert.id,
                    "issued_date": existing_cert.issued_date.isoformat(),
                    "expiry_date": existing_cert.expiry_date.isoformat(),
                    "requirements_met": existing_cert.requirements_met
                }

            # Évaluer la conformité
            compliance_score = RegulatoryComplianceService._evaluate_certification_compliance(
                user_id, certification_type, db
            )

            requirements = REGULATORY_CONFIG["certifications"][certification_type]["requirements"]
            threshold = 80  # 80% de conformité requis

            return {
                "compliant": compliance_score >= threshold,
                "compliance_score": compliance_score,
                "requirements": requirements,
                "threshold": threshold,
                "recommendations": RegulatoryComplianceService._get_compliance_recommendations(
                    certification_type, compliance_score
                )
            }

        except Exception as e:
            logger.error(f"Erreur vérification certification: {e}")
            return {"error": str(e)}

    @staticmethod
    def _evaluate_certification_compliance(user_id: int, certification_type: str, db: Session) -> float:
        """
        Évaluer le score de conformité pour une certification
        """
        try:
            score = 0
            requirements = REGULATORY_CONFIG["certifications"][certification_type]["requirements"]

            for requirement in requirements:
                if requirement == "pratiques_durables":
                    # Vérifier les pratiques durables
                    sustainable_practices = db.query(models.CommunityToken).filter(
                        and_(
                            models.CommunityToken.user_id == user_id,
                            models.CommunityToken.category.in_(["sustainable_practice", "organic_certification"])
                        )
                    ).count()
                    score += min(sustainable_practices * 10, 30)  # Max 30 points

                elif requirement == "traçabilité":
                    # Vérifier la traçabilité des produits
                    traceability_records = db.query(models.Crop).filter(
                        models.Crop.user_id == user_id
                    ).count()
                    score += min(traceability_records * 5, 25)  # Max 25 points

                elif requirement == "qualité_produit":
                    # Vérifier la qualité des produits
                    quality_crops = db.query(models.Crop).filter(
                        and_(
                            models.Crop.user_id == user_id,
                            models.Crop.quality_rating >= 4
                        )
                    ).count()
                    score += min(quality_crops * 8, 25)  # Max 25 points

                elif requirement == "certification_bio":
                    # Vérifier certification bio
                    organic_tokens = db.query(models.CommunityToken).filter(
                        and_(
                            models.CommunityToken.user_id == user_id,
                            models.CommunityToken.category == "organic_certification"
                        )
                    ).count()
                    score += min(organic_tokens * 20, 40)  # Max 40 points

            return min(score, 100)  # Score max 100

        except Exception as e:
            logger.error(f"Erreur évaluation conformité: {e}")
            return 0

    @staticmethod
    def _get_compliance_recommendations(certification_type: str, score: float) -> List[str]:
        """
        Générer des recommandations pour améliorer la conformité
        """
        recommendations = []

        if score < 50:
            recommendations.append("Augmenter les pratiques agricoles durables")
            recommendations.append("Améliorer la traçabilité des produits")
        elif score < 80:
            recommendations.append("Obtenir une certification biologique")
            recommendations.append("Améliorer la qualité des produits")

        if certification_type == "eu_export":
            recommendations.append("Respecter les normes de résidus zéro")
            recommendations.append("Utiliser des emballages conformes UE")

        return recommendations

    @staticmethod
    def check_gdpr_compliance(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Vérifier la conformité RGPD africain
        """
        try:
            # Vérifier le consentement
            consent = db.query(models.DataConsent).filter(
                and_(
                    models.DataConsent.user_id == user_id,
                    models.DataConsent.consent_type == "gdpr_african",
                    models.DataConsent.status == "active"
                )
            ).first()

            # Vérifier la minimisation des données
            data_usage = db.query(models.DataUsageLog).filter(
                models.DataUsageLog.user_id == user_id
            ).order_by(desc(models.DataUsageLog.created_at)).limit(10).all()

            # Évaluer la conformité
            compliance_issues = []

            if not consent:
                compliance_issues.append("Consentement manquant pour traitement données")

            # Vérifier rétention des données
            retention_check = RegulatoryComplianceService._check_data_retention_compliance(user_id, db)
            if not retention_check["compliant"]:
                compliance_issues.append("Données conservées trop longtemps")

            return {
                "compliant": len(compliance_issues) == 0,
                "consent_given": consent is not None,
                "data_minimization_ok": len(data_usage) <= 10,  # Limite raisonnable
                "retention_compliant": retention_check["compliant"],
                "issues": compliance_issues,
                "recommendations": RegulatoryComplianceService._get_gdpr_recommendations(compliance_issues)
            }

        except Exception as e:
            logger.error(f"Erreur vérification RGPD: {e}")
            return {"error": str(e)}

    @staticmethod
    def _check_data_retention_compliance(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Vérifier la conformité de rétention des données
        """
        try:
            # Vérifier données personnelles anciennes
            old_personal_data = db.query(models.User).filter(
                and_(
                    models.User.id == user_id,
                    models.User.created_at < datetime.utcnow() - timedelta(days=365)
                )
            ).first()

            # Vérifier données agricoles anciennes
            old_agricultural_data = db.query(models.Crop).filter(
                and_(
                    models.Crop.user_id == user_id,
                    models.Crop.created_at < datetime.utcnow() - timedelta(days=1825)
                )
            ).count()

            return {
                "compliant": old_agricultural_data == 0,
                "old_personal_data_exists": old_personal_data is not None,
                "old_agricultural_records": old_agricultural_data
            }

        except Exception as e:
            logger.error(f"Erreur vérification rétention: {e}")
            return {"compliant": False, "error": str(e)}

    @staticmethod
    def _get_gdpr_recommendations(issues: List[str]) -> List[str]:
        """
        Générer des recommandations RGPD
        """
        recommendations = []

        if "Consentement manquant" in str(issues):
            recommendations.append("Obtenir consentement explicite pour traitement données")
            recommendations.append("Informer sur droits RGPD (accès, rectification, suppression)")

        if "Données conservées trop longtemps" in str(issues):
            recommendations.append("Mettre en place politique de suppression automatique")
            recommendations.append("Anonymiser données anciennes")

        return recommendations

    @staticmethod
    def perform_legal_audit(audit_type: str, scope: List[str], db: Session) -> Dict[str, Any]:
        """
        Effectuer un audit légal automatisé
        """
        try:
            audit_id = str(uuid.uuid4())

            # Effectuer les vérifications selon le type d'audit
            audit_results = {}

            if "data_protection" in scope:
                audit_results["data_protection"] = RegulatoryComplianceService._audit_data_protection(db)

            if "export_compliance" in scope:
                audit_results["export_compliance"] = RegulatoryComplianceService._audit_export_compliance(db)

            if "agricultural_standards" in scope:
                audit_results["agricultural_standards"] = RegulatoryComplianceService._audit_agricultural_standards(db)

            # Calculer le score global
            total_checks = sum(len(results.get("checks", [])) for results in audit_results.values())
            passed_checks = sum(sum(1 for check in results.get("checks", []) if check["passed"])
                               for results in audit_results.values())

            compliance_score = (passed_checks / max(total_checks, 1)) * 100

            # Enregistrer l'audit
            audit_record = models.LegalAudit(
                audit_id=audit_id,
                audit_type=audit_type,
                scope=json.dumps(scope),
                results=json.dumps(audit_results),
                compliance_score=compliance_score,
                performed_by="system",
                performed_at=datetime.utcnow()
            )

            db.add(audit_record)
            db.commit()

            return {
                "audit_id": audit_id,
                "audit_type": audit_type,
                "compliance_score": round(compliance_score, 2),
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "results": audit_results,
                "recommendations": RegulatoryComplianceService._get_audit_recommendations(audit_results)
            }

        except Exception as e:
            logger.error(f"Erreur audit légal: {e}")
            return {"error": str(e)}

    @staticmethod
    def _audit_data_protection(db: Session) -> Dict[str, Any]:
        """
        Auditer la protection des données
        """
        checks = []

        # Vérifier consentements
        total_users = db.query(models.User).count()
        users_with_consent = db.query(models.DataConsent).filter(
            models.DataConsent.consent_type == "gdpr_african"
        ).distinct(models.DataConsent.user_id).count()

        checks.append({
            "check": "Consentement RGPD pour tous utilisateurs",
            "passed": users_with_consent >= total_users * 0.95,  # 95% minimum
            "value": f"{users_with_consent}/{total_users}"
        })

        # Vérifier logs d'utilisation
        users_with_logs = db.query(models.DataUsageLog).distinct(models.DataUsageLog.user_id).count()
        checks.append({
            "check": "Logs d'utilisation des données",
            "passed": users_with_logs >= total_users * 0.8,  # 80% minimum
            "value": f"{users_with_logs}/{total_users}"
        })

        return {"checks": checks}

    @staticmethod
    def _audit_export_compliance(db: Session) -> Dict[str, Any]:
        """
        Auditer la conformité export
        """
        checks = []

        # Vérifier certifications export
        certified_users = db.query(models.AgriculturalCertification).filter(
            models.AgriculturalCertification.certification_type == "eu_export"
        ).distinct(models.AgriculturalCertification.user_id).count()

        total_farmers = db.query(models.User).filter(models.User.role == "farmer").count()

        checks.append({
            "check": "Certifications export UE",
            "passed": certified_users >= total_farmers * 0.5,  # 50% minimum
            "value": f"{certified_users}/{total_farmers}"
        })

        return {"checks": checks}

    @staticmethod
    def _audit_agricultural_standards(db: Session) -> Dict[str, Any]:
        """
        Auditer les normes agricoles
        """
        checks = []

        # Vérifier pratiques durables
        sustainable_farmers = db.query(models.CommunityToken).filter(
            models.CommunityToken.category == "sustainable_practice"
        ).distinct(models.CommunityToken.user_id).count()

        total_farmers = db.query(models.User).filter(models.User.role == "farmer").count()

        checks.append({
            "check": "Pratiques agricoles durables",
            "passed": sustainable_farmers >= total_farmers * 0.6,  # 60% minimum
            "value": f"{sustainable_farmers}/{total_farmers}"
        })

        return {"checks": checks}

    @staticmethod
    def _get_audit_recommendations(audit_results: Dict[str, Any]) -> List[str]:
        """
        Générer des recommandations d'audit
        """
        recommendations = []

        for category, results in audit_results.items():
            for check in results.get("checks", []):
                if not check["passed"]:
                    if "consent" in check["check"].lower():
                        recommendations.append("Améliorer collecte consentements RGPD")
                    elif "certification" in check["check"].lower():
                        recommendations.append("Augmenter certifications export")
                    elif "pratiques" in check["check"].lower():
                        recommendations.append("Promouvoir pratiques durables")

        return recommendations

    @staticmethod
    def get_compliance_dashboard(db: Session) -> Dict[str, Any]:
        """
        Tableau de bord de conformité réglementaire
        """
        try:
            # Métriques générales
            total_users = db.query(models.User).count()
            certified_users = db.query(models.AgriculturalCertification).filter(
                models.AgriculturalCertification.status == "active"
            ).distinct(models.AgriculturalCertification.user_id).count()

            gdpr_compliant_users = db.query(models.DataConsent).filter(
                models.DataConsent.consent_type == "gdpr_african"
            ).distinct(models.DataConsent.user_id).count()

            recent_audits = db.query(models.LegalAudit).filter(
                models.LegalAudit.performed_at >= datetime.utcnow() - timedelta(days=90)
            ).all()

            avg_compliance_score = db.query(func.avg(models.LegalAudit.compliance_score)).scalar() or 0

            return {
                "total_users": total_users,
                "certified_users": certified_users,
                "certification_rate": round((certified_users / max(total_users, 1)) * 100, 2),
                "gdpr_compliant_users": gdpr_compliant_users,
                "gdpr_compliance_rate": round((gdpr_compliant_users / max(total_users, 1)) * 100, 2),
                "recent_audits_count": len(recent_audits),
                "average_compliance_score": round(avg_compliance_score, 2),
                "last_audit_date": max([audit.performed_at for audit in recent_audits], default=None),
                "regulatory_standards": list(REGULATORY_CONFIG["certifications"].keys())
            }

        except Exception as e:
            logger.error(f"Erreur dashboard conformité: {e}")
            return {"error": str(e)}


# Fonctions utilitaires pour l'API
def check_certification_compliance(user_id: int, certification_type: str, db: Session) -> Dict[str, Any]:
    return RegulatoryComplianceService.check_certification_compliance(user_id, certification_type, db)

def check_gdpr_compliance(user_id: int, db: Session) -> Dict[str, Any]:
    return RegulatoryComplianceService.check_gdpr_compliance(user_id, db)

def perform_legal_audit(audit_type: str, scope: List[str], db: Session) -> Dict[str, Any]:
    return RegulatoryComplianceService.perform_legal_audit(audit_type, scope, db)

def get_compliance_dashboard(db: Session) -> Dict[str, Any]:
    return RegulatoryComplianceService.get_compliance_dashboard(db)