"""
Community Tokens Service - Économie Sociale Phase 3.3
Système de récompenses pour pratiques durables

Fonctionnalités :
- Tokens communautaires pour pratiques agricoles durables
- Système de récompenses basé sur impact environnemental
- Échange tokens contre avantages communautaires
- Intégration blockchain pour traçabilité
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
from blockchain_config import BLOCKCHAIN_CONFIG

logger = logging.getLogger("community_tokens_service")

# Configuration des tokens communautaires
COMMUNITY_TOKEN_CONFIG = {
    "token_name": "AgroToken",
    "symbol": "AGRO",
    "decimals": 2,
    "total_supply": 1000000,  # 1 million de tokens
    "reward_categories": {
        "sustainable_practice": 10,  # points par pratique durable
        "carbon_reduction": 5,       # points par tonne CO2 réduite
        "biodiversity": 8,           # points par hectare biodiversité
        "water_conservation": 12,    # points par m³ d'eau économisée
        "organic_certification": 50, # points par certification bio
        "community_sharing": 15,     # points par partage connaissances
        "training_completion": 20,   # points par formation terminée
    },
    "exchange_rates": {
        "seeds": 100,      # 100 tokens = 1 sac de graines
        "fertilizer": 200, # 200 tokens = 1 sac d'engrais bio
        "tools": 300,      # 300 tokens = 1 outil agricole
        "training": 150,   # 150 tokens = 1 session formation
        "insurance": 500,  # 500 tokens = couverture assurance
    },
    "decay_rate": 0.95,   # 5% de dépréciation mensuelle si inactif
    "max_daily_reward": 100,  # Maximum 100 tokens/jour
}

class CommunityTokensService:
    """
    Service de gestion des tokens communautaires
    """

    @staticmethod
    def calculate_sustainability_score(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Calculer le score de durabilité d'un agriculteur
        """
        try:
            # Récupérer données utilisateur
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return {"error": "Utilisateur non trouvé"}

            # Calculer score basé sur pratiques
            score = 0
            practices_count = 0

            # Pratiques durables (depuis les traces blockchain)
            traces = db.query(models.BlockchainTrace).filter(
                models.BlockchainTrace.user_id == user_id
            ).all()

            for trace in traces:
                if trace.certification_type:
                    if "organic" in trace.certification_type.lower():
                        score += COMMUNITY_TOKEN_CONFIG["reward_categories"]["organic_certification"]
                        practices_count += 1
                    elif "sustainable" in trace.certification_type.lower():
                        score += COMMUNITY_TOKEN_CONFIG["reward_categories"]["sustainable_practice"]
                        practices_count += 1

            # Réduction CO2 (estimation basée sur pratiques)
            co2_reduction = practices_count * 0.5  # 0.5 tonne CO2 par pratique
            score += int(co2_reduction * COMMUNITY_TOKEN_CONFIG["reward_categories"]["carbon_reduction"])

            # Biodiversité (basé sur surface)
            biodiversity_score = min(user.total_surface * 0.1, 50)  # Max 50 points
            score += int(biodiversity_score)

            # Conservation eau (estimation)
            water_score = practices_count * 3  # 3m³ économisés par pratique
            score += int(water_score * COMMUNITY_TOKEN_CONFIG["reward_categories"]["water_conservation"] / 10)

            return {
                "user_id": user_id,
                "sustainability_score": score,
                "practices_count": practices_count,
                "co2_reduction_tonnes": co2_reduction,
                "biodiversity_score": biodiversity_score,
                "water_conservation_m3": water_score,
                "level": CommunityTokensService._get_sustainability_level(score)
            }

        except Exception as e:
            logger.error(f"Erreur calcul score durabilité: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_sustainability_level(score: int) -> str:
        """Déterminer le niveau de durabilité"""
        if score >= 500:
            return "Platine"
        elif score >= 300:
            return "Or"
        elif score >= 150:
            return "Argent"
        elif score >= 50:
            return "Bronze"
        else:
            return "Débutant"

    @staticmethod
    def award_tokens(user_id: int, category: str, amount: float, reason: str, db: Session) -> Dict[str, Any]:
        """
        Récompenser un utilisateur avec des tokens
        """
        try:
            # Vérifier limite journalière
            today = datetime.utcnow().date()
            daily_total = db.query(func.sum(models.CommunityToken.amount)).filter(
                and_(
                    models.CommunityToken.user_id == user_id,
                    models.CommunityToken.transaction_type == "reward",
                    func.date(models.CommunityToken.created_at) == today
                )
            ).scalar() or 0

            if daily_total + amount > COMMUNITY_TOKEN_CONFIG["max_daily_reward"]:
                return {"error": f"Limite journalière dépassée ({COMMUNITY_TOKEN_CONFIG['max_daily_reward']} tokens max)"}

            # Créer transaction token
            token_transaction = models.CommunityToken(
                user_id=user_id,
                amount=amount,
                transaction_type="reward",
                category=category,
                reason=reason,
                balance_after=CommunityTokensService.get_token_balance(user_id, db) + amount
            )

            db.add(token_transaction)
            db.commit()

            # Tracer sur blockchain si montant significatif
            if amount >= 10:
                try:
                    trace_data = {
                        "user_id": user_id,
                        "token_amount": amount,
                        "category": category,
                        "reason": reason,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    tx_hash = add_trace_on_chain(json.dumps(trace_data), "community_token_reward")
                    token_transaction.blockchain_tx = tx_hash
                    db.commit()
                except Exception as e:
                    logger.warning(f"Erreur blockchain token: {e}")

            return {
                "success": True,
                "transaction_id": token_transaction.id,
                "amount": amount,
                "new_balance": token_transaction.balance_after,
                "blockchain_tx": token_transaction.blockchain_tx
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur récompense tokens: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_token_balance(user_id: int, db: Session) -> float:
        """
        Récupérer le solde actuel de tokens
        """
        try:
            # Calculer solde avec dépréciation
            balance = db.query(func.sum(models.CommunityToken.amount)).filter(
                models.CommunityToken.user_id == user_id
            ).scalar() or 0

            # Appliquer dépréciation pour inactivité
            last_transaction = db.query(models.CommunityToken).filter(
                models.CommunityToken.user_id == user_id
            ).order_by(desc(models.CommunityToken.created_at)).first()

            if last_transaction:
                days_inactive = (datetime.utcnow() - last_transaction.created_at).days
                if days_inactive > 30:
                    months_inactive = days_inactive // 30
                    decay_factor = COMMUNITY_TOKEN_CONFIG["decay_rate"] ** months_inactive
                    balance = balance * decay_factor

            return round(balance, 2)

        except Exception as e:
            logger.error(f"Erreur récupération solde: {e}")
            return 0.0

    @staticmethod
    def redeem_tokens(user_id: int, item_type: str, quantity: int, db: Session) -> Dict[str, Any]:
        """
        Échanger des tokens contre des avantages
        """
        try:
            current_balance = CommunityTokensService.get_token_balance(user_id, db)
            cost_per_unit = COMMUNITY_TOKEN_CONFIG["exchange_rates"].get(item_type, 0)
            total_cost = cost_per_unit * quantity

            if current_balance < total_cost:
                return {"error": f"Solde insuffisant. Besoin: {total_cost}, Disponible: {current_balance}"}

            # Créer transaction d'échange
            redemption_transaction = models.CommunityToken(
                user_id=user_id,
                amount=-total_cost,
                transaction_type="redemption",
                category=item_type,
                reason=f"Échange {quantity}x {item_type}",
                balance_after=current_balance - total_cost
            )

            db.add(redemption_transaction)
            db.commit()

            return {
                "success": True,
                "transaction_id": redemption_transaction.id,
                "item_type": item_type,
                "quantity": quantity,
                "cost": total_cost,
                "remaining_balance": redemption_transaction.balance_after
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur échange tokens: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_token_history(user_id: int, limit: int = 50, db: Session = None) -> List[Dict[str, Any]]:
        """
        Récupérer l'historique des transactions tokens
        """
        try:
            transactions = db.query(models.CommunityToken).filter(
                models.CommunityToken.user_id == user_id
            ).order_by(desc(models.CommunityToken.created_at)).limit(limit).all()

            return [{
                "id": t.id,
                "amount": t.amount,
                "type": t.transaction_type,
                "category": t.category,
                "reason": t.reason,
                "balance_after": t.balance_after,
                "created_at": t.created_at.isoformat(),
                "blockchain_tx": t.blockchain_tx
            } for t in transactions]

        except Exception as e:
            logger.error(f"Erreur historique tokens: {e}")
            return []

    @staticmethod
    def get_community_leaderboard(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Classement communautaire des agriculteurs durables
        """
        try:
            # Calculer scores pour tous les utilisateurs actifs
            users = db.query(models.User).filter(models.User.is_active == True).all()
            leaderboard = []

            for user in users:
                score_data = CommunityTokensService.calculate_sustainability_score(user.id, db)
                balance = CommunityTokensService.get_token_balance(user.id, db)

                if score_data.get("sustainability_score", 0) > 0:
                    leaderboard.append({
                        "user_id": user.id,
                        "full_name": user.full_name,
                        "region": user.region,
                        "sustainability_score": score_data["sustainability_score"],
                        "level": score_data["level"],
                        "token_balance": balance,
                        "practices_count": score_data["practices_count"],
                        "co2_reduction": score_data["co2_reduction_tonnes"]
                    })

            # Trier par score de durabilité
            leaderboard.sort(key=lambda x: x["sustainability_score"], reverse=True)
            return leaderboard[:limit]

        except Exception as e:
            logger.error(f"Erreur leaderboard: {e}")
            return []

    @staticmethod
    def get_token_statistics(db: Session) -> Dict[str, Any]:
        """
        Statistiques globales des tokens communautaires
        """
        try:
            total_tokens = db.query(func.sum(models.CommunityToken.amount)).filter(
                models.CommunityToken.transaction_type == "reward"
            ).scalar() or 0

            active_users = db.query(models.CommunityToken.user_id).distinct().count()

            redemptions = db.query(func.sum(func.abs(models.CommunityToken.amount))).filter(
                models.CommunityToken.transaction_type == "redemption"
            ).scalar() or 0

            return {
                "total_tokens_awarded": round(total_tokens, 2),
                "active_users": active_users,
                "total_redemptions": round(redemptions, 2),
                "circulating_supply": round(total_tokens - redemptions, 2),
                "redemption_rate": round(redemptions / max(total_tokens, 1) * 100, 2),
                "average_tokens_per_user": round(total_tokens / max(active_users, 1), 2)
            }

        except Exception as e:
            logger.error(f"Erreur statistiques tokens: {e}")
            return {}


# Fonctions utilitaires pour l'API
def calculate_sustainability_score(user_id: int, db: Session) -> Dict[str, Any]:
    return CommunityTokensService.calculate_sustainability_score(user_id, db)

def award_community_tokens(user_id: int, category: str, amount: float, reason: str, db: Session) -> Dict[str, Any]:
    return CommunityTokensService.award_tokens(user_id, category, amount, reason, db)

def get_token_balance(user_id: int, db: Session) -> float:
    return CommunityTokensService.get_token_balance(user_id, db)

def redeem_community_tokens(user_id: int, item_type: str, quantity: int, db: Session) -> Dict[str, Any]:
    return CommunityTokensService.redeem_tokens(user_id, item_type, quantity, db)

def get_token_history(user_id: int, limit: int, db: Session) -> List[Dict[str, Any]]:
    return CommunityTokensService.get_token_history(user_id, limit, db)

def get_community_leaderboard(db: Session, limit: int) -> List[Dict[str, Any]]:
    return CommunityTokensService.get_community_leaderboard(db, limit)

def get_token_statistics(db: Session) -> Dict[str, Any]:
    return CommunityTokensService.get_token_statistics(db)