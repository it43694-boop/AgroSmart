"""
Service de Gamification et Réputation pour AgroSmart
Système de points, badges, niveaux et réputation
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models import User
from datetime import datetime, timedelta
import json

class GamificationService:
    def __init__(self):
        self.badges = {
            "first_order": {"name": "Premier Achat", "description": "Effectuer votre premier achat", "points": 50},
            "trusted_seller": {"name": "Vendeur de Confiance", "description": "10 ventes avec note 5 étoiles", "points": 200},
            "eco_warrior": {"name": "Guerrier Écologique", "description": "Utiliser des pratiques durables", "points": 150},
            "community_helper": {"name": "Aide Communautaire", "description": "Aider 5 autres agriculteurs", "points": 100},
            "market_master": {"name": "Maître du Marché", "description": "100 transactions réussies", "points": 500},
            "early_adopter": {"name": "Pionnier", "description": "S'inscrire dans le premier mois", "points": 100},
            "reviewer": {"name": "Critique", "description": "Écrire 10 avis", "points": 75},
            "social_butterfly": {"name": "Social", "description": "Avoir 50 connexions", "points": 125}
        }
        
        self.levels = {
            1: {"name": "Débutant", "min_points": 0, "bonus": 0},
            2: {"name": "Apprenti", "min_points": 100, "bonus": 0.05},
            3: {"name": "Agriculteur", "min_points": 500, "bonus": 0.10},
            4: {"name": "Expert", "min_points": 1500, "bonus": 0.15},
            5: {"name": "Maître", "min_points": 3000, "bonus": 0.20},
            6: {"name": "Légende", "min_points": 5000, "bonus": 0.25},
            7: {"name": "Champion", "min_points": 10000, "bonus": 0.30}
        }
    
    def get_user_level(self, points: int) -> Dict:
        """Détermine le niveau d'un utilisateur basé sur ses points"""
        level = 1
        for level_num, level_data in sorted(self.levels.items(), reverse=True):
            if points >= level_data["min_points"]:
                level = level_num
                break
        return {"level": level, **self.levels[level]}
    
    def calculate_reputation_score(self, user: User) -> Dict:
        """Calcule le score de réputation d'un utilisateur"""
        base_score = 50
        
        factors = {
            "account_age": self._calculate_account_age_score(user.created_at),
            "activity": self._calculate_activity_score(user),
            "transactions": self._calculate_transaction_score(user),
            "reviews": self._calculate_review_score(user),
            "community": self._calculate_community_score(user)
        }
        
        total_score = base_score + sum(factors.values())
        total_score = min(100, max(0, total_score))
        
        return {
            "score": total_score,
            "factors": factors,
            "rating": self._get_reputation_rating(total_score)
        }
    
    def _calculate_account_age_score(self, created_at: datetime) -> float:
        """Score basé sur l'ancienneté du compte"""
        if not created_at:
            return 0
        days = (datetime.utcnow() - created_at).days
        return min(10, days / 30)
    
    def _calculate_activity_score(self, user: User) -> float:
        """Score basé sur l'activité de l'utilisateur"""
        score = 0
        if user.last_login:
            days_since_login = (datetime.utcnow() - user.last_login).days
            if days_since_login < 7:
                score = 10
            elif days_since_login < 30:
                score = 5
        return score
    
    def _calculate_transaction_score(self, user: User) -> float:
        """Score basé sur les transactions"""
        transaction_count = len(user.marketplace_transactions)
        return min(15, transaction_count * 0.5)
    
    def _calculate_review_score(self, user: User) -> float:
        """Score basé sur les avis donnés"""
        review_count = len(user.social_posts)
        return min(10, review_count * 1)
    
    def _calculate_community_score(self, user: User) -> float:
        """Score basé sur l'engagement communautaire"""
        group_count = len(user.social_group_memberships)
        return min(5, group_count * 1)
    
    def _get_reputation_rating(self, score: float) -> str:
        """Retourne la note de réputation"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Très Bon"
        elif score >= 60:
            return "Bon"
        elif score >= 40:
            return "Moyen"
        else:
            return "À améliorer"
    
    def award_points(self, user: User, points: int, reason: str, db: Session) -> Dict:
        """Attribue des points à un utilisateur"""
        if not hasattr(user, 'gamification_points'):
            user.gamification_points = 0
        if not hasattr(user, 'gamification_level'):
            user.gamification_level = 1
        
        old_level = self.get_user_level(user.gamification_points)
        user.gamification_points += points
        new_level = self.get_user_level(user.gamification_points)
        
        level_up = new_level["level"] > old_level["level"]
        
        db.commit()
        
        return {
            "points_awarded": points,
            "total_points": user.gamification_points,
            "reason": reason,
            "level_up": level_up,
            "new_level": new_level if level_up else None
        }
    
    def award_badge(self, user: User, badge_id: str, db: Session) -> Dict:
        """Attribue un badge à un utilisateur"""
        if badge_id not in self.badges:
            return {"error": "Badge inexistant"}
        
        if not hasattr(user, 'badges'):
            user.badges = []
        
        if badge_id in user.badges:
            return {"error": "Badge déjà possédé"}
        
        user.badges.append(badge_id)
        
        badge_data = self.badges[badge_id]
        points_result = self.award_points(user, badge_data["points"], f"Badge: {badge_data['name']}", db)
        
        db.commit()
        
        return {
            "badge_id": badge_id,
            "badge": badge_data,
            "points_awarded": badge_data["points"],
            "success": True
        }
    
    def check_badges(self, user: User, db: Session) -> List[Dict]:
        """Vérifie et attribue automatiquement les badges mérités"""
        earned_badges = []
        
        if len(user.marketplace_transactions) >= 1 and "first_order" not in (user.badges or []):
            result = self.award_badge(user, "first_order", db)
            if result.get("success"):
                earned_badges.append(result)
        
        if len(user.marketplace_transactions) >= 100 and "market_master" not in (user.badges or []):
            result = self.award_badge(user, "market_master", db)
            if result.get("success"):
                earned_badges.append(result)
        
        if (datetime.utcnow() - user.created_at).days <= 30 and "early_adopter" not in (user.badges or []):
            result = self.award_badge(user, "early_adopter", db)
            if result.get("success"):
                earned_badges.append(result)
        
        return earned_badges
    
    def get_leaderboard(self, db: Session, limit: int = 10) -> List[Dict]:
        """Retourne le classement des utilisateurs"""
        users = db.query(User).filter(User.is_active == True).order_by(
            (User.gamification_points if hasattr(User, 'gamification_points') else 0).desc()
        ).limit(limit).all()
        
        leaderboard = []
        for rank, user in enumerate(users, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": user.id,
                "username": user.username or user.full_name,
                "points": getattr(user, 'gamification_points', 0),
                "level": self.get_user_level(getattr(user, 'gamification_points', 0)),
                "badges": len(getattr(user, 'badges', []))
            })
        
        return leaderboard
    
    def get_user_stats(self, user: User) -> Dict:
        """Retourne les statistiques de gamification d'un utilisateur"""
        points = getattr(user, 'gamification_points', 0)
        badges = getattr(user, 'badges', [])
        
        return {
            "points": points,
            "level": self.get_user_level(points),
            "badges": [self.badges[b] for b in badges if b in self.badges],
            "badge_count": len(badges),
            "reputation": self.calculate_reputation_score(user),
            "next_level": self._get_next_level_info(points)
        }
    
    def _get_next_level_info(self, current_points: int) -> Optional[Dict]:
        """Informations sur le niveau suivant"""
        current_level = self.get_user_level(current_points)
        next_level_num = current_level["level"] + 1
        
        if next_level_num in self.levels:
            next_level_data = self.levels[next_level_num]
            points_needed = next_level_data["min_points"] - current_points
            return {
                "level": next_level_num,
                "name": next_level_data["name"],
                "points_needed": max(0, points_needed),
                "bonus": next_level_data["bonus"]
            }
        
        return None

gamification_service = GamificationService()
