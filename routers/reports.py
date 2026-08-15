from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import datetime

from database import get_db
import auth
import models
from services.agro_brain_service import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])

report_generator = ReportGenerator()


@router.get("/weekly/{user_id}")
def generate_weekly_report(
    user_id: int,
    region: str = "Mali",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    crops = db.query(models.Crop).filter(models.Crop.user_id == user_id).all()
    crop_types = [c.crop_type for c in crops]

    try:
        report_markdown = report_generator.generate_weekly_report(
            region=region,
            crop_types=crop_types,
            user_name=current_user.full_name or "Agriculteur",
        )
        return {
            "report": report_markdown,
            "format": "markdown",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "region": region,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur génération rapport: {str(exc)}")


@router.get("/monthly/{user_id}")
def generate_monthly_report(
    user_id: int,
    region: str = "Mali",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    crops = db.query(models.Crop).filter(models.Crop.user_id == user_id).all()
    crop_types = [c.crop_type for c in crops]

    try:
        report_markdown = report_generator.generate_monthly_report(
            region=region,
            crop_types=crop_types,
            user_name=current_user.full_name or "Agriculteur",
        )
        return {
            "report": report_markdown,
            "format": "markdown",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "region": region,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur génération rapport: {str(exc)}")


@router.post("/disease-alert")
def generate_disease_alert(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not payload:
        raise HTTPException(status_code=400, detail="Payload manquant")

    disease_name = payload.get("disease_name", "Maladie inconnue")
    crop_type = payload.get("crop_type", "Culture inconnue")
    severity = payload.get("severity", "medium")

    try:
        alert_markdown = report_generator.generate_disease_alert(
            disease_name=disease_name,
            crop_type=crop_type,
            severity=severity,
        )
        return {
            "alert": alert_markdown,
            "format": "markdown",
            "disease": disease_name,
            "crop": crop_type,
            "severity": severity,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur génération alerte: {str(exc)}")
