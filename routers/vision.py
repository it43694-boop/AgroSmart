from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import datetime
import base64
import io
from PIL import Image

from database import get_db
import auth
import models
from services.computer_vision_service import PlantDiseaseDiagnostician

router = APIRouter(prefix="/api/vision", tags=["vision"])

vision_service = PlantDiseaseDiagnostician()


@router.post("/diagnose-disease")
async def diagnose_disease(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not payload:
        raise HTTPException(status_code=400, detail="Payload manquant")

    image_base64 = payload.get("image_base64")
    if not image_base64:
        raise HTTPException(status_code=400, detail="image_base64 requis")

    try:
        image_bytes = base64.b64decode(image_base64)
        image_data = io.BytesIO(image_bytes)
        result = vision_service.diagnose_from_image(image_data.getvalue())

        diagnosis_record = models.PlantDisease(
            user_id=current_user.id,
            disease_name=result.get("disease", "unknown"),
            confidence_score=result.get("confidence", 0.0),
            severity_level=result.get("severity", "unknown"),
            treatment_recommendation=result.get("treatment", ""),
            recommendations="[]",
            diagnosis_date=datetime.datetime.utcnow(),
        )
        db.add(diagnosis_record)
        db.commit()
        db.refresh(diagnosis_record)

        return {
            "diagnosis": result,
            "diagnosis_id": diagnosis_record.id,
            "saved": True,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur diagnostic maladie: {str(exc)}")
