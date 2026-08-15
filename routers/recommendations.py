from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.recommendation_service import recommendation_service

router = APIRouter(prefix="/api", tags=["recommendations"])

@router.get("/recommendations/user-based")
def get_user_based_recommendations(limit: int = 10, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    recommendations = recommendation_service.get_user_based_recommendations(current_user.id, db, limit)
    return {"recommendations": recommendations}

@router.get("/recommendations/content-based")
def get_content_based_recommendations(limit: int = 10, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    recommendations = recommendation_service.get_content_based_recommendations(current_user.id, db, limit)
    return {"recommendations": recommendations}

@router.get("/recommendations/hybrid")
def get_hybrid_recommendations(limit: int = 10, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    recommendations = recommendation_service.get_hybrid_recommendations(current_user.id, db, limit)
    return {"recommendations": recommendations}

@router.get("/recommendations/trending")
def get_trending_products(limit: int = 10, days: int = 7, db: Session = Depends(get_db)):
    trending = recommendation_service.get_trending_products(db, limit, days)
    return {"trending": trending}

@router.get("/recommendations/feed")
def get_personalized_feed(limit: int = 20, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    feed = recommendation_service.get_personalized_feed(current_user.id, db, limit)
    return feed
