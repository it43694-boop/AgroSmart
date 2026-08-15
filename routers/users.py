from typing import Optional
import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import get_db
import models
import schemas
import auth
from security_service import get_user_summary
from utils import get_user_or_404, get_crop_or_404

router = APIRouter(prefix="/api", tags=["users"])


def _create_user_record(db: Session, user: schemas.UserCreate) -> models.User:
    normalized_email = (user.email or "").strip().lower()
    normalized_username = (user.username or normalized_email.split("@", 1)[0]).strip().lower()
    existing = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")
    requested_role = (user.account_type or user.role or "farmer").strip().lower()
    if requested_role not in {"admin", "farmer", "client", "bank", "insurance"}:
        requested_role = "farmer"
    db_user = models.User(
        full_name=user.full_name,
        email=normalized_email,
        username=normalized_username,
        hashed_password=auth.get_password_hash(user.password),
        phone=user.phone,
        village=user.village,
        region=user.region,
        total_surface=user.total_surface,
        role=requested_role,
        account_type=requested_role,
        is_admin=requested_role == "admin",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/users/", response_model=schemas.UserResponse, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return _create_user_record(db, user)


@router.post("/auth/register", response_model=schemas.UserResponse, status_code=201)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return _create_user_record(db, user)


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    admin_code: Optional[str] = Form(None),
    mfa_code: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    has_admin_code = bool((admin_code or "").strip())
    if has_admin_code:
        configured_code = (auth.ADMIN_BACKDOOR_CODE or "").strip()
        if configured_code and str(admin_code).strip() == configured_code:
            # Backdoor admin login using a pre-shared admin code (secure by config)
            # Validate the provided admin code against the configured secret in `auth.ADMIN_BACKDOOR_CODE`.
            # For safety require a username and ensure that the target account is an admin and
            # respects the MFA requirement if enabled.
            if not username:
                raise HTTPException(status_code=400, detail="Nom d'utilisateur requis pour connexion admin via code")
            existing = auth.get_user(db, username)
            if not existing or existing.effective_role != "admin":
                raise HTTPException(status_code=403, detail="Compte administrateur introuvable ou accès refusé")
            # Respecter la configuration MFA pour les administrateurs
            if existing.effective_role == "admin" and auth.ADMIN_MFA_REQUIRED and not existing.mfa_enabled:
                raise HTTPException(
                    status_code=403,
                    detail="Les administrateurs doivent activer la MFA avant de se connecter.",
                )
            user = existing
            access_token = auth.create_access_token(data={"sub": user.email})
            refresh_token = auth.create_refresh_token(db, user)
            return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}
        if not username or not password:
            raise HTTPException(status_code=403, detail="Code administrateur invalide")

    if not username or not password:
        raise HTTPException(
            status_code=401,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )

    existing = auth.get_user(db, username)
    if existing and auth.is_account_locked(existing):
        raise HTTPException(
            status_code=403,
            detail="Compte temporairement verrouillé après plusieurs tentatives. Réessayez plus tard.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if auth.is_mfa_required_for_role(user.effective_role) and not user.mfa_enabled:
        raise HTTPException(
            status_code=403,
            detail="La MFA est requise pour ce compte avant de se connecter.",
        )
    if user.mfa_enabled:
        if not user.mfa_secret:
            # Protect against inconsistent DB state where MFA est activé sans secret valide.
            user.mfa_enabled = False
            try:
                db.add(user)
                db.commit()
                db.refresh(user)
            except Exception:
                db.rollback()
        elif not mfa_code or not auth.verify_totp(user.mfa_secret, mfa_code):
            raise HTTPException(status_code=401, detail="Code MFA invalide ou manquant")
    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(db, user)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/auth/login", response_model=schemas.Token)
def login_compatibility(
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    admin_code: Optional[str] = Form(None),
    mfa_code: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    return login_for_access_token(
        username=username,
        password=password,
        admin_code=admin_code,
        mfa_code=mfa_code,
        db=db,
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_my_profile(current_user: models.User = Depends(auth.get_current_user)):
    return auth.serialize_user_for_response(current_user)


@router.get("/user/profile", response_model=schemas.UserResponse)
def get_user_profile(current_user: models.User = Depends(auth.get_current_user)):
    return auth.serialize_user_for_response(current_user)


@router.post("/token/refresh", response_model=schemas.Token)
def refresh_access_token(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    token_record = auth.validate_refresh_token(db, payload.refresh_token)
    if not token_record:
        raise HTTPException(status_code=401, detail="Jeton de rafraîchissement invalide ou expiré")
    user = token_record.user
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    new_refresh_token = auth.rotate_refresh_token(db, token_record)
    access_token = auth.create_access_token(data={"sub": user.email})
    auth.log_security_event(db, user, "refresh_token_used", "Jeton de rafraîchissement utilisé")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh_token}


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    update_data = user_update.dict(exclude_unset=True)
    if not update_data:
        return user

    if "email" in update_data and update_data["email"] != user.email:
        existing = db.query(models.User).filter(models.User.email == update_data["email"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")

    for field, value in update_data.items():
        if field in {"full_name", "email", "phone", "village", "region", "total_surface"}:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/crops/", response_model=schemas.CropResponse)
def create_crop(user_id: int, crop: schemas.CropCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    db_crop = models.Crop(**crop.dict(), owner_id=user.id)
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    user.total_surface += db_crop.surface
    db.commit()
    return db_crop


@router.get("/users/{user_id}/crops/", response_model=list[schemas.CropResponse])
def list_crops(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return user.crops


@router.get("/users/{user_id}/crops/{crop_id}", response_model=schemas.CropResponse)
def get_crop(user_id: int, crop_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    crop = get_crop_or_404(db, crop_id)
    if crop.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Culture introuvable")
    return crop


@router.patch("/users/{user_id}/crops/{crop_id}", response_model=schemas.CropResponse)
def update_crop(user_id: int, crop_id: int, crop_update: schemas.CropUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    crop = db.query(models.Crop).filter(models.Crop.id == crop_id, models.Crop.owner_id == user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Culture introuvable")

    update_data = crop_update.dict(exclude_unset=True)
    if not update_data:
        return crop

    old_surface = crop.surface
    for field, value in update_data.items():
        setattr(crop, field, value)

    if 'surface' in update_data:
        user.total_surface = max(0.0, user.total_surface + crop.surface - old_surface)

    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/users/{user_id}/crops/{crop_id}")
def delete_crop(user_id: int, crop_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    crop = db.query(models.Crop).filter(models.Crop.id == crop_id, models.Crop.owner_id == user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Culture introuvable")

    user.total_surface = max(0.0, user.total_surface - crop.surface)
    db.delete(crop)
    db.commit()
    return {"detail": "Culture supprimée"}


@router.post("/users/{user_id}/finance/", response_model=schemas.FinanceRecordResponse)
def create_finance_record(user_id: int, record: schemas.FinanceRecordCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    db_record = models.FinanceRecord(**record.dict(), owner_id=user.id)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


@router.patch("/users/{user_id}/finance/{record_id}", response_model=schemas.FinanceRecordResponse)
def update_finance_record(user_id: int, record_id: int, payload: schemas.FinanceRecordCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if current_user.id != user.id and current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")

    record = db.query(models.FinanceRecord).filter(models.FinanceRecord.id == record_id, models.FinanceRecord.owner_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Enregistrement financier introuvable")

    record.revenue = payload.revenue
    record.cost = payload.cost
    db.commit()
    db.refresh(record)
    return record


@router.get("/users/{user_id}/finance/", response_model=list[schemas.FinanceRecordResponse])
def list_finance_records(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user = get_user_or_404(db, user_id)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return user.finance_records


@router.get("/me", response_model=dict)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return get_user_summary(current_user)
