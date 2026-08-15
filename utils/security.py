"""Sécurité utilitaires: timestamps timezone-aware et chiffrement optionnel pour exports"""
from datetime import datetime, timezone
import os
import base64
import logging

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_utc_iso() -> str:
    return now_utc().isoformat()


def get_export_encryption_key() -> bytes | None:
    key = os.environ.get("EXPORT_ENCRYPTION_KEY")
    if not key:
        return None

    try:
        if len(key) == 44 and key.endswith("="):
            return key.encode()
        # Derive a valid Fernet key from any passphrase by hashing it
        digest = hashlib.sha256(key.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    except Exception as e:
        logger.warning(f"Invalid EXPORT_ENCRYPTION_KEY format: {e}")
        return None


def encrypt_bytes_for_export(data: bytes) -> str | None:
    """If `EXPORT_ENCRYPTION_KEY` is set, encrypt data using Fernet and return base64 string.
    If cryptography not available or key missing, return None.
    """
    key = get_export_encryption_key()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
    except Exception:
        logger.warning("cryptography not available; skipping export encryption")
        return None

    try:
        f = Fernet(key)
        token = f.encrypt(data)
        return token.decode()
    except Exception as e:
        logger.error(f"Export encryption failed: {e}")
        return None
