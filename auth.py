import os
import secrets
import logging
import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import case, func
from sqlalchemy.orm import Session

import models
from database import SessionLocal, DATABASE_URL, get_db as database_get_db

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except Exception:  # pragma: no cover
    Fernet = None
    HAS_FERNET = False

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REFRESH_TOKEN_SINGLE_SESSION = os.getenv("REFRESH_TOKEN_SINGLE_SESSION", "false").lower() in ("1", "true", "yes")
REFRESH_TOKEN_MAX_ACTIVE_SESSIONS = int(os.getenv("REFRESH_TOKEN_MAX_ACTIVE_SESSIONS", "0"))
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))
ADMIN_MFA_REQUIRED = os.getenv("ADMIN_MFA_REQUIRED", "true").lower() in ("1", "true", "yes")
MFA_REQUIRED_ROLES = {
    role.strip().lower()
    for role in os.getenv("MFA_REQUIRED_ROLES", "admin,bank,insurance,client").split(",")
    if role.strip()
}
ADMIN_BACKDOOR_CODE = os.getenv("ADMIN_BACKDOOR_CODE")

LOG = logging.getLogger("auth")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise RuntimeError("SECRET_KEY must be set in production and must not be empty.")
    SECRET_KEY = secrets.token_urlsafe(64)
    LOG.warning("SECRET_KEY not set; using temporary runtime secret for development only.")
elif SECRET_KEY == "changeme":
    if ENVIRONMENT == "production":
        raise RuntimeError("SECRET_KEY must not be set to the insecure default 'changeme' in production.")
    SECRET_KEY = secrets.token_urlsafe(64)
    LOG.warning("SECRET_KEY is insecure default; generated temporary runtime secret for development only.")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# MFA support (optional)
try:
    import pyotp
    MFA_AVAILABLE = True
except Exception:
    MFA_AVAILABLE = False


def get_db():
    yield from database_get_db()


def serialize_user_for_response(user: Optional[models.User]) -> dict:
    if user is None:
        return {}

    raw_role = getattr(user, "role", None) or getattr(user, "account_type", None) or "farmer"
    normalized_role = str(raw_role).strip().lower()
    if normalized_role not in {"admin", "farmer", "client", "bank", "insurance"}:
        normalized_role = "farmer"

    account_type = getattr(user, "account_type", None)
    normalized_account_type = str(account_type or raw_role).strip().lower()
    if normalized_account_type not in {"admin", "farmer", "client", "bank", "insurance"}:
        normalized_account_type = normalized_role

    return {
        "id": getattr(user, "id", None),
        "full_name": getattr(user, "full_name", ""),
        "email": getattr(user, "email", None),
        "username": getattr(user, "username", None),
        "phone": getattr(user, "phone", None),
        "village": getattr(user, "village", None),
        "region": getattr(user, "region", None),
        "total_surface": getattr(user, "total_surface", 0.0),
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_validated": bool(getattr(user, "is_validated", False)),
        "account_type": normalized_account_type,
        "role": normalized_role,
        "is_active": bool(getattr(user, "is_active", True)),
        "mfa_enabled": bool(getattr(user, "mfa_enabled", False)),
        "crops": [],
        "finance_records": [],
        "loans": [],
        "insurances": [],
        "dashboard": None,
        "permissions": [],
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _get_fernet() -> Optional["Fernet"]:
    if not HAS_FERNET:
        return None

    encryption_key = os.getenv("ENCRYPTION_KEY", "").strip()
    if not encryption_key:
        encryption_key = secrets.token_urlsafe(32)
        os.environ["ENCRYPTION_KEY"] = encryption_key

    if encryption_key.startswith("gAAAAA"):
        key = encryption_key
    else:
        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest).decode("utf-8")

    return Fernet(key)


def encrypt_sensitive_data(data: str) -> str:
    fernet = _get_fernet()
    if not fernet:
        return data
    if isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = str(data).encode("utf-8")
    return fernet.encrypt(payload).decode("utf-8")


def decrypt_sensitive_data(token: str) -> str:
    fernet = _get_fernet()
    if not fernet:
        return token
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    payload = (token or "").encode("utf-8")
    digest = hmac.new(SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return digest


def verify_token(token: str, hashed_token: str) -> bool:
    try:
        if hmac.compare_digest(hash_token(token), hashed_token):
            return True
    except Exception:
        pass
    try:
        return pwd_context.verify(token, hashed_token)
    except Exception:
        return False


def generate_secure_token() -> str:
    return secrets.token_urlsafe(48)


def get_user(db: Session, email: str) -> Optional[models.User]:
    if email is None:
        return None

    normalized = (email or "").strip()
    if not normalized:
        return None

    # Prefer exact case-preserving matches first for compatibility with existing user records.
    user = db.query(models.User).filter(models.User.email == normalized).first()
    if user:
        return user

    user = db.query(models.User).filter(models.User.username == normalized).first()
    if user:
        return user

    lowercase = normalized.lower()
    # Fall back to case-insensitive lookup when exact match is not available.
    user = db.query(models.User).filter(func.lower(models.User.email) == lowercase).order_by(models.User.is_active.desc(), models.User.mfa_enabled.asc()).first()
    if user:
        return user

    return db.query(models.User).filter(func.lower(models.User.username) == lowercase).order_by(models.User.is_active.desc(), models.User.mfa_enabled.asc()).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user(db, email)
    if not user:
        return None
    if not getattr(user, "is_active", True):
        return None
    if is_account_locked(user):
        return None
    try:
        password_ok = verify_password(password, getattr(user, "hashed_password", ""))
    except Exception:
        return None
    if not password_ok:
        failed_login_attempts = getattr(user, "failed_login_attempts", 0)
        if isinstance(failed_login_attempts, (int, float)):
            failed_login_attempts = int(failed_login_attempts) + 1
        else:
            failed_login_attempts = 1
        try:
            user.failed_login_attempts = failed_login_attempts
            if failed_login_attempts >= 5:
                user.locked_until = utc_now() + timedelta(minutes=15)
            db.commit()
        except Exception:
            pass
        log_security_event(db, user, "login_failed", "Échec d'authentification par mot de passe")
        return None

    try:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = utc_now()
        db.commit()
    except Exception:
        pass
    log_security_event(db, user, "login_success", "Utilisateur connecté avec succès")
    return user


def is_account_locked(user: models.User) -> bool:
    locked_until = getattr(user, "locked_until", None)
    if not locked_until:
        return False
    if isinstance(locked_until, str):
        try:
            locked_until = datetime.fromisoformat(locked_until)
        except ValueError:
            return False
    try:
        return bool(locked_until and locked_until > utc_now())
    except TypeError:
        return False


def _get_signing_key() -> str:
    configured_key = (os.getenv("SECRET_KEY") or "").strip()
    if configured_key and configured_key != "changeme":
        return configured_key
    if SECRET_KEY:
        return SECRET_KEY
    return secrets.token_urlsafe(64)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = utc_now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    issue_time = utc_now()
    to_encode.update({
        "exp": expire,
        "iat": issue_time,
        "iss": "agrosmart",
        "nbf": issue_time,
        "jti": str(uuid.uuid4()),
    })
    signing_key = _get_signing_key()
    return jwt.encode(to_encode, signing_key, algorithm=ALGORITHM)


def _prune_refresh_token_sessions(db: Session, user: models.User) -> None:
    if REFRESH_TOKEN_SINGLE_SESSION:
        db.query(models.RefreshToken).filter(
            models.RefreshToken.user_id == user.id,
            models.RefreshToken.revoked == False,
        ).update({"revoked": True})
        db.commit()
        return

    if REFRESH_TOKEN_MAX_ACTIVE_SESSIONS > 0:
        active_tokens = (
            db.query(models.RefreshToken)
            .filter(models.RefreshToken.user_id == user.id, models.RefreshToken.revoked == False)
            .order_by(models.RefreshToken.created_at.desc())
            .all()
        )
        if len(active_tokens) >= REFRESH_TOKEN_MAX_ACTIVE_SESSIONS:
            for token in active_tokens[REFRESH_TOKEN_MAX_ACTIVE_SESSIONS - 1:]:
                token.revoked = True
            db.commit()


def create_refresh_token(db: Session, user: models.User) -> str:
    _prune_refresh_token_sessions(db, user)

    raw_token = generate_secure_token()
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = models.RefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user.id,
        expires_at=expires_at,
        jti=str(uuid.uuid4()),
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return raw_token


def validate_refresh_token(db: Session, raw_token: str) -> Optional[models.RefreshToken]:
    now = utc_now()
    token_hash = hash_token(raw_token)
    return db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash,
        models.RefreshToken.revoked == False,
        models.RefreshToken.expires_at > now,
    ).first()


def revoke_token_jti(db: Session, jti: str, token_type: str = "access", reason: Optional[str] = None) -> bool:
    if not jti:
        return False
    existing = db.query(models.TokenRevocation).filter(
        models.TokenRevocation.jti == jti,
        models.TokenRevocation.token_type == token_type,
    ).first()
    if existing:
        return True
    revocation = models.TokenRevocation(
        jti=jti,
        token_type=token_type,
        reason=reason,
    )
    db.add(revocation)
    db.commit()
    return True


def is_token_jti_revoked(db: Session, jti: str, token_type: str = "access") -> bool:
    if not jti:
        return False
    return db.query(models.TokenRevocation.id).filter(
        models.TokenRevocation.jti == jti,
        models.TokenRevocation.token_type == token_type,
    ).first() is not None


def rotate_refresh_token(db: Session, refresh_token: models.RefreshToken) -> str:
    refresh_token.revoked = True
    db.commit()
    return create_refresh_token(db, refresh_token.user)


def revoke_refresh_token(db: Session, raw_token: str, user: Optional[models.User] = None) -> bool:
    token_record = validate_refresh_token(db, raw_token)
    if not token_record:
        return False
    if user and token_record.user_id != user.id:
        return False
    token_record.revoked = True
    db.commit()
    return True


def revoke_all_refresh_tokens(db: Session, user: models.User) -> None:
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user.id,
        models.RefreshToken.revoked == False,
    ).update({"revoked": True})
    db.commit()


def create_password_reset_token(db: Session, user: models.User) -> str:
    raw_token = generate_secure_token()
    expires_at = utc_now() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    reset_token = models.PasswordResetToken(
        token_hash=hash_token(raw_token),
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return raw_token


def validate_password_reset_token(db: Session, raw_token: str) -> Optional[models.PasswordResetToken]:
    now = utc_now()
    token_hash = hash_token(raw_token)
    candidate = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token_hash == token_hash,
        models.PasswordResetToken.used == False,
        models.PasswordResetToken.expires_at > now,
    ).first()
    if candidate:
        return candidate

    legacy_candidates = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.used == False,
        models.PasswordResetToken.expires_at > now,
    ).all()
    for legacy_candidate in legacy_candidates:
        if verify_token(raw_token, legacy_candidate.token_hash):
            return legacy_candidate
    return None


def use_password_reset_token(db: Session, reset_token: models.PasswordResetToken) -> None:
    reset_token.used = True
    db.commit()


def log_security_event(db: Session, user: Optional[models.User], event: str, detail: Optional[str] = None, ip_address: Optional[str] = None) -> None:
    try:
        user_id = getattr(user, "id", None)
        if isinstance(user_id, int):
            user_id = user_id
        else:
            user_id = None

        audit_event = models.AuditLog(
            user_id=user_id,
            event=event,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(audit_event)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def is_mfa_required_for_role(role: Optional[str]) -> bool:
    return (role or "").strip().lower() in MFA_REQUIRED_ROLES


def _decode_token_to_user(token: str, db: Session) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les informations d'identification.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _get_signing_key(), algorithms=[ALGORITHM], issuer="agrosmart")
        jti = payload.get("jti")
        if jti and is_token_jti_revoked(db, str(jti), token_type="access"):
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, email=email)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    try:
        state = getattr(user, "_sa_instance_state", None)
        if state is None or getattr(state, "session", None) is None:
            db.add(user)
            db.flush()
            db.refresh(user)
    except Exception:
        pass
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database_get_db)) -> models.User:
    user = _decode_token_to_user(token, db)
    if is_mfa_required_for_role(user.effective_role) and not user.mfa_enabled:
        raise HTTPException(status_code=403, detail="La MFA est requise pour accéder à cette ressource.")
    return user


def get_current_user_allow_mfa_setup(token: str = Depends(oauth2_scheme), db: Session = Depends(database_get_db)) -> models.User:
    return _decode_token_to_user(token, db)


def validate_security_configuration() -> None:
    if ENVIRONMENT == "production":
        if not SECRET_KEY or SECRET_KEY == "changeme":
            raise RuntimeError("SECRET_KEY must be configured securely in production.")
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL must be configured in production.")
    if ALGORITHM not in {"HS256", "HS384", "HS512"}:
        raise RuntimeError("ALGORITHM must be one of HS256, HS384 or HS512.")


def get_current_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.effective_role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    if is_mfa_required_for_role(current_user.effective_role) and not current_user.mfa_enabled:
        raise HTTPException(status_code=403, detail="Les administrateurs doivent activer la MFA pour accéder à cette ressource.")
    return current_user


def decode_token_from_string(token: str, db: Session) -> models.User:
    """Helper function to decode JWT token from string."""
    return _decode_token_to_user(token, db)


async def get_current_user_optional(request: Request, db: Session = Depends(database_get_db)) -> Optional[models.User]:
    """Return the current user when a valid bearer token is present, otherwise None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    try:
        scheme, credentials = auth_header.split()
        if scheme.lower() != "bearer":
            return None
        return decode_token_from_string(credentials, db)
    except Exception:
        return None


async def get_current_admin_optional(request: Request, db: Session = Depends(database_get_db)) -> Optional[models.User]:
    """Development mode: allow requests without authentication for read-only endpoints."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        # If token provided, validate it
        try:
            scheme, credentials = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid auth scheme")
            current_user = decode_token_from_string(credentials, db)
            if current_user.effective_role != "admin":
                raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
            return current_user
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    # No token provided - allow in development mode (return None)
    return None


def get_current_farmer(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.effective_role not in ["farmer", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux agriculteurs")
    return current_user


def get_current_client(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.effective_role not in ["client", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux clients")
    return current_user


def get_current_bank(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.effective_role not in ["bank", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux banques")
    return current_user


def get_current_insurance(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.effective_role not in ["insurance", "admin"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux assurances")
    return current_user


# MFA Functions (if pyotp available)
def generate_mfa_secret(user_email: str) -> str:
    """Generate a TOTP secret for MFA"""
    if not MFA_AVAILABLE:
        raise HTTPException(status_code=500, detail="MFA non disponible")
    return pyotp.random_base32()


def verify_totp(secret: str, totp_code: str) -> bool:
    """Verify a TOTP code against a secret"""
    if not MFA_AVAILABLE:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(totp_code, valid_window=1)


def get_totp_uri(user_email: str, secret: str) -> str:
    """Get provisioning URI for QR code generation"""
    if not MFA_AVAILABLE:
        return ""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name="AgroSmart")

