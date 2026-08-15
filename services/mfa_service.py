"""
Service Multi-Factor Authentication (MFA) pour AgroSmart
Implémente TOTP (Time-based One-Time Password) avec pyotp
"""

import pyotp
import qrcode
import io
import base64
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models import User
import secrets

class MFAService:
    def __init__(self):
        self.issuer_name = "AgroSmart"
    
    def generate_secret(self) -> str:
        """Génère un secret TOTP sécurisé"""
        return pyotp.random_base32()
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """Génère des codes de récupération"""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    def setup_mfa(self, user: User, db: Session) -> dict:
        """Configure MFA pour un utilisateur sans l'activer immédiatement."""
        if user.mfa_enabled:
            return {"error": "MFA déjà activé"}
        
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        
        user.mfa_secret = secret
        user.mfa_backup_codes = ",".join(backup_codes)
        user.mfa_enabled = False
        
        db.commit()
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.issuer_name
        )
        
        qr_code = self._generate_qr_code(provisioning_uri)
        
        return {
            "secret": secret,
            "backup_codes": backup_codes,
            "qr_code": qr_code,
            "provisioning_uri": provisioning_uri
        }
    
    def verify_totp(self, user: User, token: str) -> bool:
        """Vérifie un token TOTP"""
        if not user.mfa_secret:
            return False
        
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token, valid_window=1)

    def confirm_mfa_setup(self, user: User, token: str, db: Session) -> bool:
        """Active MFA après vérification du code TOTP."""
        if not user.mfa_secret:
            return False
        
        if self.verify_totp(user, token):
            user.mfa_enabled = True
            db.commit()
            return True
        return False
    
    def verify_backup_code(self, user: User, code: str, db: Session) -> bool:
        """Vérifie et consomme un code de récupération"""
        if not user.mfa_enabled or not user.mfa_backup_codes:
            return False
        
        backup_codes = user.mfa_backup_codes.split(",")
        
        if code.upper() in backup_codes:
            backup_codes.remove(code.upper())
            user.mfa_backup_codes = ",".join(backup_codes)
            db.commit()
            return True
        
        return False
    
    def disable_mfa(self, user: User, db: Session) -> bool:
        """Désactive MFA pour un utilisateur"""
        if not user.mfa_enabled:
            return False
        
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        
        db.commit()
        return True
    
    def _generate_qr_code(self, uri: str) -> str:
        """Génère un QR code en base64"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_mfa_for_login(self, user: User, token: str, db: Session) -> Tuple[bool, str]:
        """Vérifie MFA lors de la connexion"""
        if not user.mfa_enabled:
            return True, "MFA non activé"
        
        if self.verify_totp(user, token):
            return True, "Token TOTP valide"
        
        if self.verify_backup_code(user, token, db):
            return True, "Code de récupération valide"
        
        return False, "Token MFA invalide"

mfa_service = MFAService()
