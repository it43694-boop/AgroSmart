"""
Cooperatives Integration Service - Économie Sociale Phase 3.3
API pour groupements agricoles maliens

Fonctionnalités :
- Intégration coopératives agricoles maliennes
- Gestion membres et contributions
- Partage ressources communautaires
- Coordination achats/ventes groupés
- Système de gouvernance démocratique
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
from services.blockchain_service import add_trace_on_chain, get_trace_from_chain

logger = logging.getLogger("cooperatives_service")

# Configuration des coopératives maliennes
MALI_COOPERATIVES_CONFIG = {
    "regions": {
        "Bamako": ["Union des Maraîchers de Bamako", "Coopérative Laitière du Mali"],
        "Kayes": ["Coopérative Cotonnière de Kayes", "Union des Riziculteurs"],
        "Sikasso": ["Coopérative Café-Cacao", "Groupement Anacarde"],
        "Mopti": ["Coopérative Pêcheurs", "Union Éleveurs"],
        "Tombouctou": ["Coopérative Dattes", "Groupement Pastoral"],
        "Gao": ["Coopérative Transporteurs", "Union Maraîchers Nord"]
    },
    "contribution_types": {
        "membership_fee": 5000,    # F CFA annuel
        "activity_contribution": 1000,  # F CFA par activité
        "resource_sharing": 500,   # F CFA par partage
        "training_fee": 2000,      # F CFA par formation
    },
    "governance": {
        "min_members_for_vote": 3,
        "quorum_percentage": 50,   # % de membres pour validité
        "decision_period_days": 7, # Délai pour décisions
    },
    "benefits": {
        "bulk_purchase_discount": 15,  # % de réduction achats groupés
        "shared_equipment_access": True,
        "collective_marketing": True,
        "training_subsidies": 50,   # % subvention formations
        "insurance_pool": True,
    }
}

class CooperativesService:
    """
    Service de gestion des coopératives agricoles
    """

    @staticmethod
    def create_cooperative(name: str, region: str, description: str, founder_id: int, db: Session) -> Dict[str, Any]:
        """
        Créer une nouvelle coopérative
        """
        try:
            # Vérifier que le fondateur existe
            founder = db.query(models.User).filter(models.User.id == founder_id).first()
            if not founder:
                return {"error": "Fondateur non trouvé"}

            # Créer la coopérative
            cooperative = models.Cooperative(
                name=name,
                region=region,
                description=description,
                founder_id=founder_id,
                status="active",
                governance_rules=json.dumps(MALI_COOPERATIVES_CONFIG["governance"]),
                benefits=json.dumps(MALI_COOPERATIVES_CONFIG["benefits"])
            )

            db.add(cooperative)
            db.commit()

            # Ajouter le fondateur comme membre
            founder_membership = models.CooperativeMember(
                cooperative_id=cooperative.id,
                user_id=founder_id,
                role="president",
                status="active",
                joined_at=datetime.utcnow()
            )

            db.add(founder_membership)
            db.commit()

            # Tracer sur blockchain
            try:
                trace_data = {
                    "cooperative_id": cooperative.id,
                    "name": name,
                    "region": region,
                    "founder_id": founder_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                tx_hash = add_trace_on_chain(json.dumps(trace_data), "cooperative_creation")
                cooperative.blockchain_tx = tx_hash
                db.commit()
            except Exception as e:
                logger.warning(f"Erreur blockchain coopérative: {e}")

            return {
                "success": True,
                "cooperative_id": cooperative.id,
                "name": name,
                "region": region,
                "founder": founder.full_name,
                "blockchain_tx": cooperative.blockchain_tx
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur création coopérative: {e}")
            return {"error": str(e)}

    @staticmethod
    def join_cooperative(cooperative_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Rejoindre une coopérative
        """
        try:
            # Vérifier que la coopérative existe
            cooperative = db.query(models.Cooperative).filter(models.Cooperative.id == cooperative_id).first()
            if not cooperative:
                return {"error": "Coopérative non trouvée"}

            # Vérifier que l'utilisateur n'est pas déjà membre
            existing_membership = db.query(models.CooperativeMember).filter(
                and_(
                    models.CooperativeMember.cooperative_id == cooperative_id,
                    models.CooperativeMember.user_id == user_id
                )
            ).first()

            if existing_membership:
                return {"error": "Utilisateur déjà membre de cette coopérative"}

            # Créer l'adhésion
            membership = models.CooperativeMember(
                cooperative_id=cooperative_id,
                user_id=user_id,
                role="member",
                status="pending",  # En attente d'approbation
                joined_at=datetime.utcnow()
            )

            db.add(membership)
            db.commit()

            return {
                "success": True,
                "membership_id": membership.id,
                "cooperative_name": cooperative.name,
                "status": "pending_approval",
                "message": "Demande d'adhésion soumise. En attente d'approbation."
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur adhésion coopérative: {e}")
            return {"error": str(e)}

    @staticmethod
    def approve_membership(membership_id: int, approver_id: int, db: Session) -> Dict[str, Any]:
        """
        Approuver une demande d'adhésion
        """
        try:
            # Récupérer l'adhésion
            membership = db.query(models.CooperativeMember).filter(
                models.CooperativeMember.id == membership_id
            ).first()

            if not membership:
                return {"error": "Adhésion non trouvée"}

            # Vérifier que l'approbateur est autorisé (président ou admin)
            cooperative = db.query(models.Cooperative).filter(
                models.Cooperative.id == membership.cooperative_id
            ).first()

            approver_membership = db.query(models.CooperativeMember).filter(
                and_(
                    models.CooperativeMember.cooperative_id == membership.cooperative_id,
                    models.CooperativeMember.user_id == approver_id,
                    models.CooperativeMember.role.in_(["president", "admin"])
                )
            ).first()

            if not approver_membership:
                return {"error": "Non autorisé à approuver les adhésions"}

            # Approuver l'adhésion
            membership.status = "active"
            membership.approved_at = datetime.utcnow()
            membership.approved_by = approver_id

            db.commit()

            return {
                "success": True,
                "membership_id": membership.id,
                "user_id": membership.user_id,
                "cooperative_name": cooperative.name,
                "status": "approved"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur approbation adhésion: {e}")
            return {"error": str(e)}

    @staticmethod
    def record_contribution(cooperative_id: int, user_id: int, contribution_type: str, amount: float, description: str, db: Session) -> Dict[str, Any]:
        """
        Enregistrer une contribution à la coopérative
        """
        try:
            # Vérifier que l'utilisateur est membre actif
            membership = db.query(models.CooperativeMember).filter(
                and_(
                    models.CooperativeMember.cooperative_id == cooperative_id,
                    models.CooperativeMember.user_id == user_id,
                    models.CooperativeMember.status == "active"
                )
            ).first()

            if not membership:
                return {"error": "Utilisateur non membre actif de cette coopérative"}

            # Créer la contribution
            contribution = models.CooperativeContribution(
                cooperative_id=cooperative_id,
                user_id=user_id,
                contribution_type=contribution_type,
                amount=amount,
                description=description,
                status="completed"
            )

            db.add(contribution)
            db.commit()

            return {
                "success": True,
                "contribution_id": contribution.id,
                "type": contribution_type,
                "amount": amount,
                "cooperative_id": cooperative_id
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur enregistrement contribution: {e}")
            return {"error": str(e)}

    @staticmethod
    def create_group_purchase(cooperative_id: int, product_name: str, quantity_needed: float, budget_max: float, organizer_id: int, db: Session) -> Dict[str, Any]:
        """
        Créer un achat groupé coopératif
        """
        try:
            # Vérifier que l'organisateur est membre
            membership = db.query(models.CooperativeMember).filter(
                and_(
                    models.CooperativeMember.cooperative_id == cooperative_id,
                    models.CooperativeMember.user_id == organizer_id,
                    models.CooperativeMember.status == "active"
                )
            ).first()

            if not membership:
                return {"error": "Organisateur non membre actif"}

            # Créer l'achat groupé
            group_purchase = models.CooperativeGroupPurchase(
                cooperative_id=cooperative_id,
                product_name=product_name,
                quantity_needed=quantity_needed,
                budget_max=budget_max,
                organizer_id=organizer_id,
                status="open",
                created_at=datetime.utcnow()
            )

            db.add(group_purchase)
            db.commit()

            return {
                "success": True,
                "purchase_id": group_purchase.id,
                "product_name": product_name,
                "quantity_needed": quantity_needed,
                "budget_max": budget_max,
                "status": "open"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur création achat groupé: {e}")
            return {"error": str(e)}

    @staticmethod
    def join_group_purchase(purchase_id: int, user_id: int, quantity_committed: float, db: Session) -> Dict[str, Any]:
        """
        Rejoindre un achat groupé
        """
        try:
            # Récupérer l'achat groupé
            purchase = db.query(models.CooperativeGroupPurchase).filter(
                models.CooperativeGroupPurchase.id == purchase_id
            ).first()

            if not purchase or purchase.status != "open":
                return {"error": "Achat groupé non disponible"}

            # Vérifier que l'utilisateur est membre de la coopérative
            membership = db.query(models.CooperativeMember).filter(
                and_(
                    models.CooperativeMember.cooperative_id == purchase.cooperative_id,
                    models.CooperativeMember.user_id == user_id,
                    models.CooperativeMember.status == "active"
                )
            ).first()

            if not membership:
                return {"error": "Non membre de cette coopérative"}

            # Vérifier que la quantité n'excède pas le besoin
            current_committed = db.query(func.sum(models.CooperativePurchaseParticipant.quantity_committed)).filter(
                models.CooperativePurchaseParticipant.purchase_id == purchase_id
            ).scalar() or 0

            if current_committed + quantity_committed > purchase.quantity_needed:
                return {"error": f"Quantité trop élevée. Restant: {purchase.quantity_needed - current_committed}"}

            # Créer la participation
            participant = models.CooperativePurchaseParticipant(
                purchase_id=purchase_id,
                user_id=user_id,
                quantity_committed=quantity_committed,
                status="committed"
            )

            db.add(participant)
            db.commit()

            return {
                "success": True,
                "participant_id": participant.id,
                "purchase_id": purchase_id,
                "quantity_committed": quantity_committed
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur participation achat groupé: {e}")
            return {"error": str(e)}

    @staticmethod
    def list_group_purchases(
        cooperative_id: int, db: Session, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            query = db.query(models.CooperativeGroupPurchase).filter(
                models.CooperativeGroupPurchase.cooperative_id == cooperative_id
            )
            if status:
                query = query.filter(models.CooperativeGroupPurchase.status == status)
            purchases = query.order_by(models.CooperativeGroupPurchase.created_at.desc()).all()
            result = []
            for purchase in purchases:
                committed = db.query(func.sum(models.CooperativePurchaseParticipant.quantity_committed)).filter(
                    models.CooperativePurchaseParticipant.purchase_id == purchase.id
                ).scalar() or 0
                result.append({
                    "id": purchase.id,
                    "cooperative_id": purchase.cooperative_id,
                    "product_name": purchase.product_name,
                    "quantity_needed": purchase.quantity_needed,
                    "quantity_committed": float(committed),
                    "budget_max": purchase.budget_max,
                    "organizer_id": purchase.organizer_id,
                    "status": purchase.status,
                    "created_at": purchase.created_at,
                })
            return result
        except Exception as e:
            logger.error(f"Erreur liste achats groupés: {e}")
            return []

    @staticmethod
    def get_cooperative_dashboard(cooperative_id: int, db: Session) -> Dict[str, Any]:
        """
        Tableau de bord d'une coopérative
        """
        try:
            cooperative = db.query(models.Cooperative).filter(models.Cooperative.id == cooperative_id).first()
            if not cooperative:
                return {"error": "Coopérative non trouvée"}

            # Statistiques membres
            total_members = db.query(func.count(models.CooperativeMember.id)).filter(
                and_(
                    models.CooperativeMember.cooperative_id == cooperative_id,
                    models.CooperativeMember.status == "active"
                )
            ).scalar()

            # Contributions totales
            total_contributions = db.query(func.sum(models.CooperativeContribution.amount)).filter(
                models.CooperativeContribution.cooperative_id == cooperative_id
            ).scalar() or 0

            # Achats groupés actifs
            active_purchases = db.query(models.CooperativeGroupPurchase).filter(
                and_(
                    models.CooperativeGroupPurchase.cooperative_id == cooperative_id,
                    models.CooperativeGroupPurchase.status == "open"
                )
            ).count()

            # Membres récents (30 derniers jours)
            recent_members = db.query(func.count(models.CooperativeMember.id)).filter(
                and_(
                    models.CooperativeMember.cooperative_id == cooperative_id,
                    models.CooperativeMember.joined_at >= datetime.utcnow() - timedelta(days=30)
                )
            ).scalar()

            return {
                "cooperative_id": cooperative_id,
                "name": cooperative.name,
                "region": cooperative.region,
                "founder": cooperative.founder.full_name if cooperative.founder else "N/A",
                "total_members": total_members,
                "total_contributions": round(total_contributions, 2),
                "active_group_purchases": active_purchases,
                "recent_members": recent_members,
                "created_at": cooperative.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Erreur dashboard coopérative: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_available_cooperatives(region: Optional[str] = None, db: Session = None) -> List[Dict[str, Any]]:
        """
        Lister les coopératives disponibles
        """
        try:
            query = db.query(models.Cooperative).filter(models.Cooperative.status == "active")

            if region:
                query = query.filter(models.Cooperative.region == region)

            cooperatives = query.all()

            result = []
            for coop in cooperatives:
                member_count = db.query(func.count(models.CooperativeMember.id)).filter(
                    and_(
                        models.CooperativeMember.cooperative_id == coop.id,
                        models.CooperativeMember.status == "active"
                    )
                ).scalar()

                result.append({
                    "id": coop.id,
                    "name": coop.name,
                    "region": coop.region,
                    "description": coop.description,
                    "member_count": member_count,
                    "founder": coop.founder.full_name if coop.founder else "N/A",
                    "created_at": coop.created_at.isoformat()
                })

            return result

        except Exception as e:
            logger.error(f"Erreur liste coopératives: {e}")
            return []

    @staticmethod
    def get_cooperative_statistics(db: Session) -> Dict[str, Any]:
        """
        Statistiques globales des coopératives
        """
        try:
            total_cooperatives = db.query(models.Cooperative).count()

            active_cooperatives = db.query(models.Cooperative).filter(
                models.Cooperative.status == "active"
            ).count()

            total_members = db.query(models.CooperativeMember).filter(
                models.CooperativeMember.status == "active"
            ).count()

            total_contributions = db.query(func.sum(models.CooperativeContribution.amount)).scalar() or 0

            group_purchases = db.query(models.CooperativeGroupPurchase).count()

            return {
                "total_cooperatives": total_cooperatives,
                "active_cooperatives": active_cooperatives,
                "total_members": total_members,
                "total_contributions": round(total_contributions, 2),
                "group_purchases_count": group_purchases,
                "average_members_per_cooperative": round(total_members / max(total_cooperatives, 1), 2),
                "average_contribution_per_member": round(total_contributions / max(total_members, 1), 2)
            }

        except Exception as e:
            logger.error(f"Erreur statistiques coopératives: {e}")
            return {}

    @staticmethod
    def get_mali_cooperatives_templates() -> Dict[str, Any]:
        """
        Templates de coopératives maliennes par région
        """
        return {
            "regions": MALI_COOPERATIVES_CONFIG["regions"],
            "contribution_types": MALI_COOPERATIVES_CONFIG["contribution_types"],
            "governance": MALI_COOPERATIVES_CONFIG["governance"],
            "benefits": MALI_COOPERATIVES_CONFIG["benefits"]
        }


# Fonctions utilitaires pour l'API
def create_cooperative(name: str, region: str, description: str, founder_id: int, db: Session) -> Dict[str, Any]:
    return CooperativesService.create_cooperative(name, region, description, founder_id, db)

def join_cooperative(cooperative_id: int, user_id: int, db: Session) -> Dict[str, Any]:
    return CooperativesService.join_cooperative(cooperative_id, user_id, db)

def approve_cooperative_membership(membership_id: int, approver_id: int, db: Session) -> Dict[str, Any]:
    return CooperativesService.approve_membership(membership_id, approver_id, db)

def record_cooperative_contribution(cooperative_id: int, user_id: int, contribution_type: str, amount: float, description: str, db: Session) -> Dict[str, Any]:
    return CooperativesService.record_contribution(cooperative_id, user_id, contribution_type, amount, description, db)

def create_group_purchase(cooperative_id: int, product_name: str, quantity_needed: float, budget_max: float, organizer_id: int, db: Session) -> Dict[str, Any]:
    return CooperativesService.create_group_purchase(cooperative_id, product_name, quantity_needed, budget_max, organizer_id, db)

def join_group_purchase(purchase_id: int, user_id: int, quantity_committed: float, db: Session) -> Dict[str, Any]:
    return CooperativesService.join_group_purchase(purchase_id, user_id, quantity_committed, db)

def get_cooperative_dashboard(cooperative_id: int, db: Session) -> Dict[str, Any]:
    return CooperativesService.get_cooperative_dashboard(cooperative_id, db)

def get_available_cooperatives(region: Optional[str], db: Session) -> List[Dict[str, Any]]:
    return CooperativesService.get_available_cooperatives(region, db)

def get_mali_cooperatives_templates() -> Dict[str, Any]:
    return CooperativesService.get_mali_cooperatives_templates()

def get_cooperative_statistics(db: Session) -> Dict[str, Any]:
    return CooperativesService.get_cooperative_statistics(db)


def list_cooperative_group_purchases(
    cooperative_id: int, db: Session, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    return CooperativesService.list_group_purchases(cooperative_id, db, status)


def list_cooperative_group_purchases(
    cooperative_id: int, db: Session, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    return CooperativesService.list_group_purchases(cooperative_id, db, status)