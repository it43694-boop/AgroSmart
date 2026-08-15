"""
Impact Tracking Service - Économie Sociale Phase 3.3
Mesure réduction pauvreté et émissions CO2

Fonctionnalités :
- Suivi d'impact social et environnemental
- Mesure réduction pauvreté et émissions CO2
- Métriques 1000+ agriculteurs actifs
- Rapports d'impact communautaire
- Intégration données blockchain
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, extract

import models
import schemas
from services.blockchain_service import get_trace_from_chain

logger = logging.getLogger("impact_tracking_service")

# Configuration du suivi d'impact
IMPACT_CONFIG = {
    "metrics": {
        "poverty_reduction": {
            "income_increase_target": 25,  # % augmentation revenu cible
            "households_lifted": 1000,     # Ménages sortis pauvreté
            "measurement_period_months": 12
        },
        "carbon_reduction": {
            "co2_target_tonnes": 50000,   # Tonnes CO2 réduites cible/an
            "measurement_methods": ["satellite", "ground_survey", "modeling"],
            "verification_frequency_days": 90
        },
        "biodiversity": {
            "species_protection_target": 50,  # Espèces protégées
            "habitat_restoration_ha": 1000,   # Hectares restaurés
        },
        "water_conservation": {
            "water_savings_target_m3": 100000,  # m³ économisés
            "irrigation_efficiency_target": 70,  # % efficacité
        }
    },
    "reporting": {
        "frequency": "quarterly",  # mensuel, trimestriel, annuel
        "stakeholders": ["government", "ngo", "community", "investors"],
        "transparency_level": "public"  # public, private, restricted
    },
    "targets": {
        "active_farmers": 1000,
        "women_farmers_percentage": 40,
        "youth_farmers_percentage": 30,
        "organic_certified_percentage": 60,
        "digital_adoption_percentage": 80
    }
}

class ImpactTrackingService:
    """
    Service de suivi d'impact social et environnemental
    """

    @staticmethod
    def calculate_poverty_reduction_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
        """
        Calculer les métriques de réduction de pauvreté
        """
        try:
            # Période d'analyse
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_months * 30)

            # Récupérer données utilisateurs actifs
            active_users = db.query(models.User).filter(
                and_(
                    models.User.is_active == True,
                    models.User.created_at <= end_date
                )
            ).all()

            total_households = len(active_users)
            baseline_income = 0
            current_income = 0
            households_above_poverty = 0

            poverty_line = 2000  # F CFA/jour ligne pauvreté Mali

            for user in active_users:
                # Revenu de base (estimation initiale)
                baseline = user.total_surface * 50000  # Estimation 50k F CFA/ha/an

                # Revenu actuel (basé sur transactions et pratiques)
                marketplace_sales = db.query(func.sum(models.MarketplaceTransaction.amount)).filter(
                    and_(
                        models.MarketplaceTransaction.seller_id == user.id,
                        models.MarketplaceTransaction.created_at >= start_date
                    )
                ).scalar() or 0

                token_rewards = db.query(func.sum(models.CommunityToken.amount)).filter(
                    and_(
                        models.CommunityToken.user_id == user.id,
                        models.CommunityToken.transaction_type == "reward",
                        models.CommunityToken.created_at >= start_date
                    )
                ).scalar() or 0

                # Conversion tokens en valeur (estimation)
                current = baseline + marketplace_sales + (token_rewards * 100)  # 100 F CFA/token

                baseline_income += baseline
                current_income += current

                if current >= poverty_line * 365:  # Revenu annuel
                    households_above_poverty += 1

            # Calculs métriques
            income_increase_percentage = ((current_income - baseline_income) / max(baseline_income, 1)) * 100
            poverty_reduction_rate = (households_above_poverty / max(total_households, 1)) * 100

            return {
                "period_months": period_months,
                "total_households": total_households,
                "households_above_poverty_line": households_above_poverty,
                "poverty_reduction_rate": round(poverty_reduction_rate, 2),
                "average_income_increase": round(income_increase_percentage, 2),
                "baseline_income_total": round(baseline_income, 2),
                "current_income_total": round(current_income, 2),
                "target_achievement": round((households_above_poverty / IMPACT_CONFIG["metrics"]["poverty_reduction"]["households_lifted"]) * 100, 2)
            }

        except Exception as e:
            logger.error(f"Erreur calcul métriques pauvreté: {e}")
            return {"error": str(e)}

    @staticmethod
    def calculate_carbon_reduction_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
        """
        Calculer les métriques de réduction CO2
        """
        try:
            # Période d'analyse
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_months * 30)

            # Récupérer traces blockchain pour pratiques durables
            traces = db.query(models.BlockchainTrace).filter(
                and_(
                    models.BlockchainTrace.created_at >= start_date,
                    models.BlockchainTrace.certification_type.isnot(None)
                )
            ).all()

            total_co2_reduction = 0
            practices_count = 0
            hectares_impacted = 0

            # Facteurs d'émission par pratique (tonnes CO2/ha/an)
            co2_factors = {
                "organic_farming": 2.5,      # Réduction vs agriculture conventionnelle
                "conservation_agriculture": 1.8,
                "agroforestry": 3.2,
                "water_conservation": 1.0,
                "renewable_energy": 4.0
            }

            for trace in traces:
                if trace.certification_type:
                    cert_type = trace.certification_type.lower()

                    # Trouver facteur correspondant
                    factor = 0
                    for key, value in co2_factors.items():
                        if key in cert_type:
                            factor = value
                            break

                    if factor > 0:
                        # Estimation surface impactée (hectare)
                        surface = getattr(trace, 'surface_impacted', 1.0)  # Valeur par défaut si non spécifiée
                        reduction = surface * factor
                        total_co2_reduction += reduction
                        practices_count += 1
                        hectares_impacted += surface

            # Métriques supplémentaires depuis tokens communautaires
            token_rewards = db.query(func.sum(models.CommunityToken.amount)).filter(
                and_(
                    models.CommunityToken.transaction_type == "reward",
                    models.CommunityToken.category == "carbon_reduction",
                    models.CommunityToken.created_at >= start_date
                )
            ).scalar() or 0

            # Chaque token = 0.1 tonne CO2 réduite
            additional_co2 = token_rewards * 0.1
            total_co2_reduction += additional_co2

            return {
                "period_months": period_months,
                "total_co2_reduction_tonnes": round(total_co2_reduction, 2),
                "practices_count": practices_count,
                "hectares_impacted": round(hectares_impacted, 2),
                "average_co2_per_hectare": round(total_co2_reduction / max(hectares_impacted, 1), 2),
                "target_achievement": round((total_co2_reduction / IMPACT_CONFIG["metrics"]["carbon_reduction"]["co2_target_tonnes"]) * 100, 2),
                "verification_status": "pending"  # À implémenter avec données satellite
            }

        except Exception as e:
            logger.error(f"Erreur calcul métriques CO2: {e}")
            return {"error": str(e)}

    @staticmethod
    def calculate_biodiversity_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
        """
        Calculer les métriques de biodiversité
        """
        try:
            # Période d'analyse
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_months * 30)

            # Récupérer pratiques biodiversité
            biodiversity_traces = db.query(models.BlockchainTrace).filter(
                and_(
                    models.BlockchainTrace.created_at >= start_date,
                    models.BlockchainTrace.certification_type.like("%biodiversity%")
                )
            ).all()

            species_protected = 0
            habitat_restored = 0
            corridors_created = 0

            for trace in biodiversity_traces:
                # Estimation basée sur données trace
                if hasattr(trace, 'species_count'):
                    species_protected += trace.species_count
                else:
                    species_protected += 5  # Estimation par défaut

                if hasattr(trace, 'habitat_area'):
                    habitat_restored += trace.habitat_area
                else:
                    habitat_restored += 1.0  # 1 ha par défaut

                corridors_created += 1  # Un corridor par trace

            return {
                "period_months": period_months,
                "species_protected": species_protected,
                "habitat_restored_hectares": round(habitat_restored, 2),
                "biodiversity_corridors": corridors_created,
                "species_target_achievement": round((species_protected / IMPACT_CONFIG["metrics"]["biodiversity"]["species_protection_target"]) * 100, 2),
                "habitat_target_achievement": round((habitat_restored / IMPACT_CONFIG["metrics"]["biodiversity"]["habitat_restoration_ha"]) * 100, 2)
            }

        except Exception as e:
            logger.error(f"Erreur calcul métriques biodiversité: {e}")
            return {"error": str(e)}

    @staticmethod
    def calculate_water_conservation_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
        """
        Calculer les métriques de conservation eau
        """
        try:
            # Période d'analyse
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_months * 30)

            # Récupérer pratiques conservation eau
            water_traces = db.query(models.BlockchainTrace).filter(
                and_(
                    models.BlockchainTrace.created_at >= start_date,
                    or_(
                        models.BlockchainTrace.certification_type.like("%water%"),
                        models.BlockchainTrace.certification_type.like("%irrigation%")
                    )
                )
            ).all()

            water_saved = 0
            irrigation_efficiency = 0
            practices_count = 0

            for trace in water_traces:
                # Estimation économies d'eau
                if hasattr(trace, 'water_saved_m3'):
                    water_saved += trace.water_saved_m3
                else:
                    # Estimation basée sur surface
                    surface = getattr(trace, 'surface_impacted', 1.0)
                    water_saved += surface * 1000  # 1000 m³/ha économisés

                if hasattr(trace, 'irrigation_efficiency'):
                    irrigation_efficiency += trace.irrigation_efficiency
                    practices_count += 1
                else:
                    irrigation_efficiency += 65  # Efficacité moyenne
                    practices_count += 1

            avg_efficiency = irrigation_efficiency / max(practices_count, 1)

            return {
                "period_months": period_months,
                "water_saved_m3": round(water_saved, 2),
                "average_irrigation_efficiency": round(avg_efficiency, 2),
                "water_conservation_practices": practices_count,
                "water_target_achievement": round((water_saved / IMPACT_CONFIG["metrics"]["water_conservation"]["water_savings_target_m3"]) * 100, 2),
                "efficiency_target_achievement": round((avg_efficiency / IMPACT_CONFIG["metrics"]["water_conservation"]["irrigation_efficiency_target"]) * 100, 2)
            }

        except Exception as e:
            logger.error(f"Erreur calcul métriques eau: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_platform_adoption_metrics(db: Session) -> Dict[str, Any]:
        """
        Métriques d'adoption de la plateforme
        """
        try:
            # Utilisateurs actifs
            active_farmers = db.query(func.count(models.User.id)).filter(
                models.User.is_active == True
            ).scalar()

            # Répartition par genre
            women_farmers = 0
            if hasattr(models.User, 'gender'):
                women_farmers = db.query(func.count(models.User.id)).filter(
                    and_(
                        models.User.is_active == True,
                        models.User.gender == "female"
                    )
                ).scalar()

            # Jeunes agriculteurs (< 35 ans)
            youth_farmers = 0
            if hasattr(models.User, 'date_of_birth'):
                youth_farmers = db.query(func.count(models.User.id)).filter(
                    and_(
                        models.User.is_active == True,
                        extract('year', func.age(models.User.date_of_birth)) < 35
                    )
                ).scalar()

            # Certifications bio
            organic_certified = db.query(func.count(models.BlockchainTrace.id)).filter(
                models.BlockchainTrace.certification_type.like("%organic%")
            ).scalar()

            # Adoption digitale (utilisateurs avec transactions récentes)
            digital_users = db.query(models.User.id).filter(
                and_(
                    models.User.is_active == True,
                    models.User.id.in_(
                        db.query(models.MarketplaceTransaction.seller_id).filter(
                            models.MarketplaceTransaction.created_at >= datetime.utcnow() - timedelta(days=30)
                        ).subquery()
                    )
                )
            ).distinct().count()

            # Calculs pourcentages
            women_percentage = (women_farmers / max(active_farmers, 1)) * 100
            youth_percentage = (youth_farmers / max(active_farmers, 1)) * 100
            organic_percentage = (organic_certified / max(active_farmers, 1)) * 100
            digital_percentage = (digital_users / max(active_farmers, 1)) * 100

            return {
                "active_farmers": active_farmers,
                "women_farmers_percentage": round(women_percentage, 2),
                "youth_farmers_percentage": round(youth_percentage, 2),
                "organic_certified_percentage": round(organic_percentage, 2),
                "digital_adoption_percentage": round(digital_percentage, 2),
                "targets": IMPACT_CONFIG["targets"],
                "target_achievements": {
                    "active_farmers": round((active_farmers / IMPACT_CONFIG["targets"]["active_farmers"]) * 100, 2),
                    "women_farmers": round((women_percentage / IMPACT_CONFIG["targets"]["women_farmers_percentage"]) * 100, 2),
                    "youth_farmers": round((youth_percentage / IMPACT_CONFIG["targets"]["youth_farmers_percentage"]) * 100, 2),
                    "organic_certified": round((organic_percentage / IMPACT_CONFIG["targets"]["organic_certified_percentage"]) * 100, 2),
                    "digital_adoption": round((digital_percentage / IMPACT_CONFIG["targets"]["digital_adoption_percentage"]) * 100, 2)
                }
            }

        except Exception as e:
            logger.error(f"Erreur métriques adoption: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_impact_report(db: Session, report_type: str = "comprehensive", period_months: int = 12, stakeholder: str = None) -> Dict[str, Any]:
        """
        Générer un rapport d'impact complet
        """
        try:
            report = {
                "report_type": report_type,
                "period_months": period_months,
                "generated_at": datetime.utcnow().isoformat(),
                "platform_metrics": ImpactTrackingService.get_platform_adoption_metrics(db)
            }

            if stakeholder:
                report["stakeholder_focus"] = stakeholder
                summary_label = stakeholder.lower()
                if summary_label == "b2g":
                    report["executive_summary"] = (
                        "Rapport B2G préparé pour les décideurs publics et les financeurs, "
                        "avec des indicateurs de transformation sociale, alimentaire et climatique."
                    )
                elif summary_label == "b2b":
                    report["executive_summary"] = (
                        "Rapport B2B orienté vers les partenariats commerciaux, "
                        "la chaîne de valeur responsable et la traçabilité durable."
                    )
                else:
                    report["executive_summary"] = (
                        "Rapport d'impact adapté aux besoins du stakeholder indiqué."
                    )

            if report_type in ["comprehensive", "poverty"]:
                report["poverty_reduction"] = ImpactTrackingService.calculate_poverty_reduction_metrics(db, period_months)

            if report_type in ["comprehensive", "carbon"]:
                report["carbon_reduction"] = ImpactTrackingService.calculate_carbon_reduction_metrics(db, period_months)

            if report_type in ["comprehensive", "biodiversity"]:
                report["biodiversity"] = ImpactTrackingService.calculate_biodiversity_metrics(db, period_months)

            if report_type in ["comprehensive", "water"]:
                report["water_conservation"] = ImpactTrackingService.calculate_water_conservation_metrics(db, period_months)

            # Calcul score d'impact global
            if report_type == "comprehensive":
                achievements = report["platform_metrics"]["target_achievements"]
                poverty_achievement = report["poverty_reduction"].get("target_achievement", 0)
                carbon_achievement = report["carbon_reduction"].get("target_achievement", 0)

                overall_score = (
                    achievements["active_farmers"] * 0.2 +
                    achievements["women_farmers"] * 0.15 +
                    achievements["youth_farmers"] * 0.15 +
                    achievements["organic_certified"] * 0.15 +
                    achievements["digital_adoption"] * 0.15 +
                    poverty_achievement * 0.1 +
                    carbon_achievement * 0.1
                )

                report["overall_impact_score"] = round(overall_score, 2)

            return report

        except Exception as e:
            logger.error(f"Erreur génération rapport impact: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_impact_dashboard(db: Session) -> Dict[str, Any]:
        """
        Tableau de bord d'impact en temps réel
        """
        try:
            # Métriques clés
            active_farmers = db.query(func.count(models.User.id)).filter(
                models.User.is_active == True
            ).scalar()

            total_transactions = db.query(func.count(models.MarketplaceOrder.id)).scalar()

            total_co2_reduction = db.query(func.sum(models.CommunityToken.amount)).filter(
                models.CommunityToken.category == "carbon_reduction"
            ).scalar() or 0
            total_co2_reduction = total_co2_reduction * 0.1  # Conversion tokens

            total_token_rewards = db.query(func.sum(models.CommunityToken.amount)).filter(
                models.CommunityToken.transaction_type == "reward"
            ).scalar() or 0

            cooperatives_count = db.query(func.count(models.Cooperative.id)).filter(
                models.Cooperative.status == "active"
            ).scalar()

            return {
                "active_farmers": active_farmers,
                "total_marketplace_transactions": total_transactions,
                "total_co2_reduction_tonnes": round(total_co2_reduction, 2),
                "total_community_tokens_awarded": round(total_token_rewards, 2),
                "active_cooperatives": cooperatives_count,
                "last_updated": datetime.utcnow().isoformat(),
                "targets": IMPACT_CONFIG["targets"]
            }

        except Exception as e:
            logger.error(f"Erreur dashboard impact: {e}")
            return {"error": str(e)}


# Fonctions utilitaires pour l'API
def calculate_poverty_reduction_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
    return ImpactTrackingService.calculate_poverty_reduction_metrics(db, period_months)

def calculate_carbon_reduction_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
    return ImpactTrackingService.calculate_carbon_reduction_metrics(db, period_months)

def calculate_biodiversity_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
    return ImpactTrackingService.calculate_biodiversity_metrics(db, period_months)

def calculate_water_conservation_metrics(db: Session, period_months: int = 12) -> Dict[str, Any]:
    return ImpactTrackingService.calculate_water_conservation_metrics(db, period_months)

def get_platform_adoption_metrics(db: Session) -> Dict[str, Any]:
    return ImpactTrackingService.get_platform_adoption_metrics(db)

def generate_impact_report(db: Session, report_type: str = "comprehensive", period_months: int = 12, stakeholder: str = None) -> Dict[str, Any]:
    return ImpactTrackingService.generate_impact_report(db, report_type, period_months, stakeholder)

def get_impact_dashboard(db: Session) -> Dict[str, Any]:
    return ImpactTrackingService.get_impact_dashboard(db)