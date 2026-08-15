"""Admin user management routes - Block, unblock, validate, delete users."""
from fastapi import APIRouter, Depends, HTTPException
import datetime
import secrets
from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from utils import get_user_or_404
import schemas
from services import admin_service

router = APIRouter(prefix="/api", tags=["admin_users"])


def _normalize_admin_role(role: str | None) -> str:
    allowed = {"admin", "farmer", "client", "bank", "insurance"}
    if not role:
        return "farmer"
    normalized = str(role).strip().lower()
    if normalized in {"agriculteur", "farmer"}:
        return "farmer"
    if normalized in {"banque", "bank"}:
        return "bank"
    if normalized in {"assurance", "insurance"}:
        return "insurance"
    if normalized in {"admin", "client"}:
        return normalized
    return normalized if normalized in allowed else "farmer"


def _build_admin_password() -> str:
    # Keep the bootstrap-friendly default path simple but sufficiently strong for a generated account.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789abcdefghijkmnopqrstuvwxyz!@#$%&*"
    return "Agri" + "".join(secrets.choice(alphabet) for _ in range(12))


@router.post("/admin/users/", status_code=201)
def create_user_via_admin(payload: dict, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Admin UI contract for creating a partner/user profile from the admin console."""
    raw_name = payload.get("full_name") or payload.get("name") or payload.get("fullName")
    email = payload.get("email") or payload.get("contact_email")
    role = _normalize_admin_role(payload.get("role") or payload.get("account_type"))

    if not raw_name or not str(raw_name).strip():
        raise HTTPException(status_code=400, detail="Nom complet requis")
    if not email or not str(email).strip():
        raise HTTPException(status_code=400, detail="Email requis")

    normalized_email = str(email).strip().lower()
    existing = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

    password = _build_admin_password()
    username = str(payload.get("username") or normalized_email.split("@", 1)[0]).strip().lower()
    if not username:
        username = normalized_email.split("@", 1)[0]

    user = models.User(
        full_name=str(raw_name).strip(),
        email=normalized_email,
        username=username,
        hashed_password=auth.get_password_hash(password),
        phone=(payload.get("phone") or payload.get("contact_phone") or None),
        village=payload.get("village") or None,
        region=payload.get("region") or None,
        total_surface=float(payload.get("total_surface") or 0.0),
        role=role,
        account_type=role,
        is_admin=(role == "admin"),
        is_active=True,
        is_validated=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_create_user", f"Utilisateur {user.email} créé depuis l'admin")
    return {
        "status": "success",
        "user_id": user.id,
        "role": user.role,
        "email": user.email,
        "generated_password": password,
        "message": "Utilisateur créé", 
    }


@router.post("/admin/banks/", status_code=201)
def create_bank_partner(payload: dict, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Create a bank-partner user record accepted by the admin console."""
    event_payload = {
        "name": payload.get("name") or payload.get("full_name") or payload.get("fullName"),
        "email": payload.get("email") or payload.get("contact_email"),
        "phone": payload.get("phone") or payload.get("contact_phone"),
        "code": payload.get("code") or payload.get("identifier") or payload.get("bank_code"),
        "role": "bank",
    }
    if not event_payload["name"]:
        raise HTTPException(status_code=400, detail="Nom de banque requis")
    if not event_payload["email"]:
        raise HTTPException(status_code=400, detail="Email contact requis")

    return create_user_via_admin({
        "name": event_payload["name"],
        "email": event_payload["email"],
        "phone": event_payload["phone"],
        "role": "bank",
        "account_type": "bank",
        "region": payload.get("region") or None,
    }, db=db, current_admin=current_admin)


@router.post("/admin/insurances/", status_code=201)
def create_insurance_partner(payload: dict, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Create an insurance-partner user record accepted by the admin console."""
    event_payload = {
        "name": payload.get("name") or payload.get("full_name") or payload.get("fullName"),
        "email": payload.get("email") or payload.get("contact_email"),
        "phone": payload.get("phone") or payload.get("contact_phone"),
        "code": payload.get("code") or payload.get("identifier") or payload.get("insurance_code"),
        "role": "insurance",
    }
    if not event_payload["name"]:
        raise HTTPException(status_code=400, detail="Nom de compagnie requis")
    if not event_payload["email"]:
        raise HTTPException(status_code=400, detail="Email contact requis")

    return create_user_via_admin({
        "name": event_payload["name"],
        "email": event_payload["email"],
        "phone": event_payload["phone"],
        "role": "insurance",
        "account_type": "insurance",
        "region": payload.get("region") or None,
    }, db=db, current_admin=current_admin)


@router.put("/admin/users/{user_id}/block/")
def block_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Block/deactivate a user."""
    user = get_user_or_404(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas bloquer votre propre compte")
    
    user.is_active = False
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_block_user", f"Utilisateur {user.email} bloqué")
    
    return {
        "status": "success",
        "user_id": user.id,
        "is_active": user.is_active,
        "message": "Utilisateur bloqué"
    }


@router.put("/admin/users/{user_id}/unblock/")
def unblock_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Unblock/reactivate a user."""
    user = get_user_or_404(db, user_id)
    
    user.is_active = True
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_unblock_user", f"Utilisateur {user.email} débloqué")
    
    return {
        "status": "success",
        "user_id": user.id,
        "is_active": user.is_active,
        "message": "Utilisateur débloqué"
    }


@router.put("/admin/users/{user_id}/validate/")
def validate_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Validate a user account."""
    user = get_user_or_404(db, user_id)
    
    user.is_validated = True
    user.is_active = True
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_validate_user", f"Utilisateur {user.email} validé")
    
    return {
        "status": "success",
        "user_id": user.id,
        "is_validated": user.is_validated,
        "message": "Utilisateur validé"
    }


@router.put("/admin/users/{user_id}/reject/")
def reject_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Reject a pending account and keep it inactive."""
    user = get_user_or_404(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas rejeter votre propre compte")

    user.is_validated = False
    user.is_active = False
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    auth.log_security_event(db, current_admin, "admin_reject_user", f"Utilisateur {user.email} rejeté")

    return {
        "status": "success",
        "user_id": user.id,
        "is_validated": user.is_validated,
        "is_active": user.is_active,
        "message": "Utilisateur rejeté"
    }


@router.delete("/admin/users/{user_id}/")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    """Delete a user account."""
    user = get_user_or_404(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    
    email = user.email
    db.delete(user)
    db.commit()
    auth.log_security_event(db, current_admin, "admin_delete_user", f"Utilisateur {email} supprimé")
    
    return {
        "status": "success",
        "user_id": user_id,
        "message": "Utilisateur supprimé"
    }


# --- Admin dashboard & summaries (couvrent frontend/admin.html expectations)
@router.get("/admin/stats/", response_model=schemas.AdminStatsResponse)
def admin_stats(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    return admin_service.get_admin_stats(db)


@router.get("/admin/crops/")
def admin_crops(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    return admin_service.get_admin_crops_summary(db)


@router.get("/admin/finance/")
def admin_finance(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    return admin_service.get_admin_finance_summary(db)


@router.get("/admin/dashboard/")
def admin_dashboard(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    stats = admin_service.get_admin_stats(db)
    crops = admin_service.get_admin_crops_summary(db)
    finance = admin_service.get_admin_finance_summary(db)
    return {"stats": stats, "crops": crops, "finance": finance}


# Alerts endpoints
@router.get("/admin/alerts/", response_model=list[schemas.AlertResponse])
def list_alerts(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
    return alerts


@router.get("/admin/alerts/{alert_id}/", response_model=schemas.AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    return alert


@router.put("/admin/alerts/{alert_id}/mark_read/")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return {"status": "success", "alert_id": alert.id, "is_read": alert.is_read}


# Support endpoints
@router.get("/admin/support/", response_model=list[schemas.SupportMessageResponse])
def list_support(db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    msgs = db.query(models.SupportMessage).order_by(models.SupportMessage.created_at.desc()).all()
    return msgs


@router.get("/admin/support/{message_id}/", response_model=schemas.SupportMessageResponse)
def get_support_message(message_id: int, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    msg = db.query(models.SupportMessage).filter(models.SupportMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message support introuvable")
    return msg


@router.put("/admin/support/{message_id}/respond/", response_model=schemas.SupportMessageResponse)
def respond_support_message(message_id: int, payload: schemas.SupportRespondRequest, db: Session = Depends(get_db), current_admin: models.User = Depends(auth.get_current_admin)):
    msg = db.query(models.SupportMessage).filter(models.SupportMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message support introuvable")
    msg.response = payload.response
    msg.responded_at = datetime.datetime.utcnow()
    msg.status = "RESPONDED"
    db.commit()
    db.refresh(msg)
    try:
        auth.log_security_event(db, current_admin, "admin_respond_support", f"Réponse au message support #{msg.id}")
    except Exception:
        pass
    return msg


# --- Debug endpoints (dev only) -------------------------------------------------
@router.get("/debug/whoami/")
def debug_whoami(current_user: models.User = Depends(auth.get_current_user)):
    """Return serialized current user for testing tokens and auth."""
    return auth.serialize_user_for_response(current_user)
