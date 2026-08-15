"""Voice API routes - Voice commands and history"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import datetime

from database import get_db
import models
import auth
from services.voice_service import process_voice_input, generate_voice_output, get_voice_languages, get_voice_language_info

router = APIRouter(prefix="/api/voice", tags=["voice"])

# In-memory history for tests and lightweight runtime
VOICE_HISTORY: list[dict] = []


@router.post("/command/")
def process_voice_command(
    command: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user_optional)
):
    """Process a voice command from the user"""
    try:
        # Accept multiple possible input keys used by clients/tests
        command_text = command.get("text") or command.get("command") or command.get("recognized_text") or ""
        language_hint = command.get("language") or command.get("language_detected") or "fr"
        
        # Use the voice service to process the command
        result = process_voice_input(text=command_text, language_hint=language_hint)
        
        # Generate voice response
        response = generate_voice_output(result)
        
        return {
            "success": True,
            "result": {
                "recognized_text": result["text"],
                "language": result["language"],
                "intent": result["intent"],
                "entities": result["entities"],
                "confidence": result["confidence"],
                "timestamp": result["timestamp"],
            },
            "response": {
                "text": response["text"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur traitement commande: {str(e)}")


@router.post("/history/")
def save_voice_command(
    command: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user_optional)
):
    """Save a voice command to history"""
    try:
        # Process the command first (accept several payload shapes)
        command_text = command.get("recognized_text") or command.get("text") or command.get("command") or ""
        language_hint = command.get("language_detected") or command.get("language") or "fr"
        result = process_voice_input(text=command_text, language_hint=language_hint)
        
        # En prod: sauvegarder dans la base de données
        history_entry = {
            "user_id": getattr(current_user, "id", None),
            "recognized_text": result["text"],
            "language": result["language"],
            "intent": result["intent"],
            "entities": result["entities"],
            "confidence": result["confidence"],
            "timestamp": result["timestamp"]
        }

        # persist in-memory for the running app (tests expect retrieval)
        VOICE_HISTORY.append(history_entry)
        return {
            "success": True,
            "entry": history_entry
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde: {str(e)}")


@router.get("/history/")
def get_voice_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user_optional)
):
    """Get voice command history for the current user"""
    try:
        # Mock history (en prod: depuis la base de données)
        history = [
            {
                "id": 1,
                "recognized_text": "Afficher la météo",
                "language": "fr",
                "intent": "weather",
                "confidence": 0.85,
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            {
                "id": 2,
                "recognized_text": "Voir les prix du marché",
                "language": "fr",
                "intent": "market",
                "confidence": 0.92,
                "timestamp": (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
            }
        ]
        
        # Merge persisted history with sample history (persisted entries first)
        combined = list(VOICE_HISTORY) + history
        return {
            "user_id": getattr(current_user, "id", None),
            "items": combined,
            "total": len(combined)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur historique: {str(e)}")


@router.get("/languages/")
def get_supported_languages(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user_optional)
):
    """Get supported voice languages"""
    try:
        languages = get_voice_languages()
        return {
            "languages": languages,
            "total": len(languages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur langues: {str(e)}")


@router.get("/languages/{language}/")
def get_language_info(
    language: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user_optional)
):
    """Get information about a specific language"""
    try:
        info = get_voice_language_info(language)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur info langue: {str(e)}")
