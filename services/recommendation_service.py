"""
Service de Recommandations Collaboratives pour AgroSmart
Système de recommandation basé sur le filtrage collaboratif et le contenu
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import User, MarketplaceTransaction, Crop
from collections import defaultdict
import math

class RecommendationService:
    def __init__(self):
        self.min_common_items = 2
        self.min_similarity = 0.1
    
    def get_user_based_recommendations(self, user_id: int, db: Session, limit: int = 10) -> List[Dict]:
        """Recommandations basées sur les utilisateurs similaires (User-based CF)"""
        user_transactions = db.query(MarketplaceTransaction).filter(
            MarketplaceTransaction.seller_id == user_id
        ).all()
        
        if len(user_transactions) < self.min_common_items:
            return self.get_content_based_recommendations(user_id, db, limit)
        
        user_items = {t.listing_id for t in user_transactions}
        
        all_users = db.query(User).filter(User.id != user_id, User.is_active == True).all()
        
        similarities = []
        for other_user in all_users:
            other_transactions = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.seller_id == other_user.id
            ).all()
            other_items = {t.listing_id for t in other_transactions}
            
            common_items = user_items & other_items
            if len(common_items) >= self.min_common_items:
                similarity = self._calculate_cosine_similarity(user_items, other_items)
                if similarity >= self.min_similarity:
                    similarities.append((other_user.id, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = defaultdict(float)
        for other_user_id, similarity in similarities[:20]:
            other_transactions = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.seller_id == other_user_id
            ).all()
            
            for transaction in other_transactions:
                if transaction.listing_id not in user_items:
                    recommendations[transaction.listing_id] += similarity
        
        sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        
        return self._format_recommendations(sorted_recommendations[:limit], db)
    
    def get_content_based_recommendations(self, user_id: int, db: Session, limit: int = 10) -> List[Dict]:
        """Recommandations basées sur le contenu (Content-based CF)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        user_crops = db.query(Crop).filter(Crop.owner_id == user_id).all()
        if not user_crops:
            return self._get_popular_listings(db, limit)
        
        user_categories = {crop.category for crop in user_crops if crop.category}
        user_regions = {user.region} if user.region else set()
        
        all_listings = db.query(MarketplaceTransaction).filter(
            MarketplaceTransaction.seller_id != user_id
        ).all()
        
        scored_listings = []
        for transaction in all_listings:
            score = 0
            if transaction.listing and transaction.listing.category in user_categories:
                score += 2
            if transaction.seller and transaction.seller.region in user_regions:
                score += 1
            
            if score > 0:
                scored_listings.append((transaction.listing_id, score))
        
        scored_listings.sort(key=lambda x: x[1], reverse=True)
        
        return self._format_recommendations(scored_listings[:limit], db)
    
    def get_hybrid_recommendations(self, user_id: int, db: Session, limit: int = 10) -> List[Dict]:
        """Recommandations hybrides combinant user-based et content-based"""
        user_based = self.get_user_based_recommendations(user_id, db, limit * 2)
        content_based = self.get_content_based_recommendations(user_id, db, limit * 2)
        
        combined_scores = defaultdict(float)
        
        for rec in user_based:
            combined_scores[rec['id']] += rec.get('score', 1.0) * 0.6
        
        for rec in content_based:
            combined_scores[rec['id']] += rec.get('score', 1.0) * 0.4
        
        sorted_recommendations = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        return self._format_recommendations(sorted_recommendations[:limit], db)
    
    def _calculate_cosine_similarity(self, set1: set, set2: set) -> float:
        """Calcule la similarité cosinus entre deux ensembles"""
        intersection = len(set1 & set2)
        if intersection == 0:
            return 0.0
        
        magnitude = math.sqrt(len(set1)) * math.sqrt(len(set2))
        return intersection / magnitude if magnitude > 0 else 0.0
    
    def _format_recommendations(self, recommendations: List[Tuple], db: Session) -> List[Dict]:
        """Formate les recommandations pour l'API"""
        formatted = []
        for listing_id, score in recommendations:
            transaction = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.listing_id == listing_id
            ).first()
            
            if transaction and transaction.listing:
                formatted.append({
                    "id": listing_id,
                    "title": transaction.listing.title,
                    "price": transaction.listing.price_per_unit,
                    "category": transaction.listing.category,
                    "score": score,
                    "seller": transaction.seller.full_name if transaction.seller else "Unknown"
                })
        
        return formatted
    
    def _get_popular_listings(self, db: Session, limit: int) -> List[Dict]:
        """Retourne les listings les plus populaires"""
        from sqlalchemy import func
        
        popular = db.query(
            MarketplaceTransaction.listing_id,
            func.count(MarketplaceTransaction.id).label('count')
        ).group_by(MarketplaceTransaction.listing_id).order_by(
            func.count(MarketplaceTransaction.id).desc()
        ).limit(limit).all()
        
        formatted = []
        for listing_id, count in popular:
            transaction = db.query(MarketplaceTransaction).filter(
                MarketplaceTransaction.listing_id == listing_id
            ).first()
            
            if transaction and transaction.listing:
                formatted.append({
                    "id": listing_id,
                    "title": transaction.listing.title,
                    "price": transaction.listing.price_per_unit,
                    "category": transaction.listing.category,
                    "score": count,
                    "seller": transaction.seller.full_name if transaction.seller else "Unknown"
                })
        
        return formatted
    
    def get_trending_products(self, db: Session, limit: int = 10, days: int = 7) -> List[Dict]:
        """Retourne les produits tendance sur les derniers jours"""
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = db.query(
            MarketplaceTransaction.listing_id,
            func.count(MarketplaceTransaction.id).label('count')
        ).filter(
            MarketplaceTransaction.created_at >= cutoff_date
        ).group_by(MarketplaceTransaction.listing_id).order_by(
            func.count(MarketplaceTransaction.id).desc()
        ).limit(limit).all()
        
        return self._format_recommendations(trending, db)
    
    def get_personalized_feed(self, user_id: int, db: Session, limit: int = 20) -> Dict:
        """Génère un feed personnalisé pour l'utilisateur"""
        hybrid_recs = self.get_hybrid_recommendations(user_id, db, limit // 2)
        trending = self.get_trending_products(db, limit // 2)
        
        combined = []
        seen_ids = set()
        
        for rec in hybrid_recs:
            if rec['id'] not in seen_ids:
                rec['reason'] = 'Recommandé pour vous'
                combined.append(rec)
                seen_ids.add(rec['id'])
        
        for rec in trending:
            if rec['id'] not in seen_ids:
                rec['reason'] = 'Tendance'
                combined.append(rec)
                seen_ids.add(rec['id'])
        
        return {
            "recommendations": combined[:limit],
            "total": len(combined)
        }

recommendation_service = RecommendationService()
