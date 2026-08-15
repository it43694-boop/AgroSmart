from fastapi import HTTPException
from sqlalchemy.orm import Session
import models


def get_user_or_404(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user


def get_crop_or_404(db: Session, crop_id: int) -> models.Crop:
    crop = db.query(models.Crop).filter(models.Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Culture introuvable")
    return crop


def _raise_service_error(result: dict, status_code: int = 400):
    if isinstance(result, dict):
        if result.get("error"):
            raise HTTPException(status_code=status_code, detail=result["error"])
        if result.get("success") is False:
            raise HTTPException(status_code=status_code, detail=result.get("error", "Opération échouée"))
