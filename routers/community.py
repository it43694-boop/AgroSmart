import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from services.social_training_service import (
    create_social_group,
    list_social_groups,
    join_social_group,
    create_social_post,
    list_social_posts,
    add_comment,
    list_post_comments,
    like_social_post,
)
from utils import _raise_service_error

router = APIRouter(prefix="/api", tags=["community"])

COLLABORATION_APPOINTMENTS: list[dict] = []
COLLABORATION_CHAT_HISTORY: list[dict] = []
COLLABORATION_SIGNALING_MESSAGES: list[dict] = []
COLLABORATION_APPOINTMENT_SEQ = 1
COLLABORATION_SESSION_SEQ = 1


@router.post("/collaboration/appointments/")
def create_collaboration_appointment(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    global COLLABORATION_APPOINTMENT_SEQ
    appointment = {
        "id": COLLABORATION_APPOINTMENT_SEQ,
        "expert_name": payload.get("expert_name", "Expert Agro"),
        "expert_specialty": payload.get("expert_specialty", "agronomie"),
        "scheduled_at": payload.get("scheduled_at", datetime.datetime.utcnow().isoformat()),
        "topic": payload.get("topic", "Consultation agricole virtuelle"),
        "farm_location": payload.get("farm_location", "0.0,0.0"),
        "created_by": current_user.email,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "status": "scheduled",
    }
    COLLABORATION_APPOINTMENTS.append(appointment)
    COLLABORATION_APPOINTMENT_SEQ += 1
    return appointment


@router.get("/collaboration/appointments/")
def list_collaboration_appointments(current_user: models.User = Depends(auth.get_current_user)):
    return COLLABORATION_APPOINTMENTS


@router.post("/collaboration/signaling/")
def collaboration_signaling(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    signaling_message = {
        "appointment_id": payload.get("appointment_id"),
        "type": payload.get("type"),
        "message": payload.get("message"),
        "sender": current_user.email,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    COLLABORATION_SIGNALING_MESSAGES.append(signaling_message)
    return {"success": True, "message": "Signaling message reçu"}


@router.post("/collaboration/chat/")
def collaboration_chat(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    chat_message = {
        "appointment_id": payload.get("appointment_id"),
        "sender_name": payload.get("sender_name", current_user.full_name if hasattr(current_user, "full_name") else current_user.email),
        "message": payload.get("message", ""),
        "message_type": payload.get("message_type", "text"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    COLLABORATION_CHAT_HISTORY.append(chat_message)
    return {"success": True, "message": chat_message}


@router.post("/collaboration/webrtc/sessions/")
def create_webrtc_session(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    global COLLABORATION_SESSION_SEQ
    session = {
        "session_id": COLLABORATION_SESSION_SEQ,
        "appointment_id": payload.get("appointment_id"),
        "session_type": payload.get("session_type", "video"),
        "participant_ids": payload.get("participant_ids", []),
        "status": "created",
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    COLLABORATION_SESSION_SEQ += 1
    return session


@router.post("/community/groups/", response_model=schemas.SocialGroupResponse)
def create_social_group_endpoint(group: schemas.SocialGroupCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_social_group(current_user.id, group.dict(), db)
    return db.query(models.SocialGroup).filter(models.SocialGroup.id == result["group_id"]).first()


@router.get("/community/groups/", response_model=list[schemas.SocialGroupResponse])
def get_social_groups(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_social_groups(db)


@router.post("/community/groups/{group_id}/join/")
def join_social_group_endpoint(group_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return join_social_group(current_user.id, group_id, db)


@router.post("/community/posts/", response_model=schemas.SocialPostResponse)
def create_social_post_endpoint(post: schemas.SocialPostCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_social_post(current_user.id, post.dict(), db)
    return db.query(models.SocialPost).filter(models.SocialPost.id == result["post_id"]).first()


@router.get("/community/posts/", response_model=list[schemas.SocialPostResponse])
def get_social_posts(group_id: Optional[int] = None, experience_share: Optional[bool] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_social_posts(db, group_id, experience_share)


@router.post("/community/posts/{post_id}/comments/", response_model=schemas.SocialCommentResponse)
def add_comment_endpoint(post_id: int, comment: schemas.SocialCommentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = add_comment(current_user.id, post_id, comment.dict(), db)
    return db.query(models.SocialComment).filter(models.SocialComment.id == result["comment_id"]).first()


@router.get("/community/posts/{post_id}/comments/", response_model=list[schemas.SocialCommentResponse])
def get_post_comments_endpoint(post_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_post_comments(post_id, db)


@router.post("/community/posts/{post_id}/like/")
def like_post_endpoint(post_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = like_social_post(current_user.id, post_id, db)
    _raise_service_error(result)
    return result
