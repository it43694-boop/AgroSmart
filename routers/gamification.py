from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.gamification_service import gamification_service

router = APIRouter(prefix="/api", tags=["gamification"])

@router.get("/gamification/stats")
def get_gamification_stats(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    stats = gamification_service.get_user_stats(current_user)
    return stats

@router.post("/gamification/points")
def award_points(points: int, reason: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    result = gamification_service.award_points(current_user, points, reason, db)
    return result

@router.post("/gamification/badges/{badge_id}")
def award_badge(badge_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    result = gamification_service.award_badge(current_user, badge_id, db)
    return result

@router.post("/gamification/check-badges")
def check_badges(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    earned_badges = gamification_service.check_badges(current_user, db)
    return {"earned_badges": earned_badges}

@router.get("/gamification/leaderboard")
def get_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    leaderboard = gamification_service.get_leaderboard(db, limit)
    return {"leaderboard": leaderboard}

@router.get("/gamification/reputation")
def get_reputation(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    reputation = gamification_service.calculate_reputation_score(current_user)
    return reputation
