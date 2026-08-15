from typing import Optional
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from security_service import get_user_summary
from utils import get_user_or_404, send_password_reset_email
from services.mfa_service import mfa_service

router = APIRouter(prefix="/api", tags=["security"])


@router.post("/auth/mfa/setup", response_model=dict)
def auth_setup_mfa(payload: schemas.MFASetupRequest, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect")
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="La MFA est déjà activée pour ce compte.")
    result = mfa_service.setup_mfa(user, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "secret": result["secret"],
        "backup_codes": result["backup_codes"],
        "qr_code": result["qr_code"],
        "message": "Scannez ce code QR avec votre app d'authentification (Google Authenticator, Authy, etc.)",
    }


@router.post("/auth/mfa/verify", response_model=dict)
def auth_verify_mfa(payload: schemas.MFAAuthVerifyRequest, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect")
    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="Aucun secret MFA trouvé. Lancez d'abord la configuration MFA.")
    if not mfa_service.confirm_mfa_setup(user, payload.totp_code, db):
        raise HTTPException(status_code=400, detail="Code TOTP invalide")
    return {
        "status": "success",
        "message": "MFA activé avec succès",
        "mfa_enabled": True,
    }


@router.post("/mfa/setup", response_model=dict)
def setup_mfa(current_user: models.User = Depends(auth.get_current_user_allow_mfa_setup), db: Session = Depends(get_db)):
    result = mfa_service.setup_mfa(current_user, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "secret": result["secret"],
        "backup_codes": result["backup_codes"],
        "qr_code": result["qr_code"],
        "message": "Scannez ce code QR avec votre app d'authentification (Google Authenticator, Authy, etc.)",
    }


@router.post("/mfa/verify", response_model=dict)
def verify_mfa_setup(payload: schemas.MFASetupVerifyRequest, current_user: models.User = Depends(auth.get_current_user_allow_mfa_setup), db: Session = Depends(get_db)):
    if not mfa_service.confirm_mfa_setup(current_user, payload.totp_code, db):
        raise HTTPException(status_code=400, detail="Code TOTP invalide")
    return {
        "status": "success",
        "message": "MFA activé avec succès",
        "mfa_enabled": True,
    }


@router.post("/mfa/disable", response_model=dict)
def disable_mfa(payload: schemas.MFADisableRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not auth.verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    return {
        "status": "success",
        "message": "MFA désactivé",
        "mfa_enabled": False,
    }


@router.post("/password-reset/request", response_model=dict)
def request_password_reset(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        token = auth.create_password_reset_token(db, user)
        send_password_reset_email(user, token)
        auth.log_security_event(db, user, "password_reset_requested", "Demande de réinitialisation de mot de passe")
    return {
        "status": "success",
        "message": "Si cette adresse email existe, un lien de réinitialisation a été envoyé.",
    }


@router.post("/password-reset/confirm", response_model=dict)
def confirm_password_reset(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    reset_record = auth.validate_password_reset_token(db, payload.token)
    if not reset_record:
        raise HTTPException(status_code=400, detail="Jeton de réinitialisation invalide ou expiré")
    user = reset_record.user
    user.hashed_password = auth.get_password_hash(payload.new_password)
    auth.revoke_all_refresh_tokens(db, user)
    auth.use_password_reset_token(db, reset_record)
    auth.log_security_event(db, user, "password_reset_completed", "Mot de passe réinitialisé")
    return {
        "status": "success",
        "message": "Mot de passe réinitialisé avec succès.",
    }


@router.put("/admin/users/{user_id}/role", response_model=dict)
def update_user_role(user_id: int, payload: schemas.AdminRoleUpdateRequest, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    user = get_user_or_404(db, user_id)
    new_role = payload.role
    if new_role not in ["admin", "farmer", "client", "bank", "insurance"]:
        raise HTTPException(status_code=400, detail="Rôle invalide. Valeurs acceptées: admin, farmer, client, bank, insurance")
    if user.id == current_admin.id and new_role != "admin":
        raise HTTPException(status_code=400, detail="Un admin ne peut pas se retirer du rôle admin")
    user.role = new_role
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_role_update", f"Rôle de l'utilisateur {user.email} mis à jour en '{new_role}'")
    return {
        "status": "success",
        "user_id": user.id,
        "role": user.role,
        "message": f"Rôle mis à jour en '{new_role}'",
    }


@router.put("/admin/users/{user_id}/status", response_model=dict)
def update_user_status(user_id: int, payload: schemas.AdminStatusUpdateRequest, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    user = get_user_or_404(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")
    user.is_active = payload.is_active
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    status_text = "activé" if user.is_active else "désactivé"
    auth.log_security_event(db, current_admin, "admin_status_update", f"Statut de l'utilisateur {user.email} changé en {status_text}")
    return {
        "status": "success",
        "user_id": user.id,
        "is_active": user.is_active,
        "message": f"Compte {status_text}",
    }


@router.get("/admin/users/", response_model=list)
@router.get("/admin/users", response_model=list)
def list_all_users(skip: int = 0, limit: int = 50, role: Optional[str] = None, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    users = query.offset(skip).limit(limit).all()
    return [get_user_summary(u) for u in users]
