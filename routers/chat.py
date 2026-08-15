from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
import datetime

from database import get_db
import auth
import models
from services.agro_brain_service import MultilingualChatbot

router = APIRouter(prefix="/api/chat", tags=["chat"])

chat_service = MultilingualChatbot()


@router.post("/message")
def chat_message(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not payload:
        raise HTTPException(status_code=400, detail="Payload manquant")

    message = payload.get("message", "")
    language = payload.get("language", "fr")
    if not message:
        raise HTTPException(status_code=400, detail="message requis")

    try:
        response = chat_service.chat(message, language)
        chat_msg = models.ChatMessage(
            user_id=current_user.id,
            session_id=str(current_user.id),
            message_type="user",
            content=message,
            language=response.get("language", language),
            intent_detected=response.get("intent", "general"),
            response_generated=response.get("text", ""),
            context_data="{}",
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(chat_msg)
        db.commit()
        db.refresh(chat_msg)

        return {
            "response": response,
            "message_id": chat_msg.id,
            "timestamp": chat_msg.timestamp.isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur chatbot: {str(exc)}")


@router.get("/history/{user_id}")
def get_chat_history(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == user_id)
        .order_by(models.ChatMessage.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": msg.id,
            "user_message": msg.content,
            "ai_response": msg.response_generated,
            "language": msg.language,
            "intent": msg.intent_detected,
            "created_at": msg.timestamp.isoformat(),
        }
        for msg in messages
    ]
