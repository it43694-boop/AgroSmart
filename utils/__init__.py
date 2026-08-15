"""
Utils - Fonctions utilitaires générales
"""
import os
import smtplib
import ssl
from socket import gaierror
from email.message import EmailMessage
import models


def get_user_or_404(db, user_id: int):
    """Retourne un `models.User` ou lève `HTTPException(404)` si introuvable."""
    from fastapi import HTTPException
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user


def get_crop_or_404(db, crop_id: int):
    """Retourne un `models.Crop` ou lève `HTTPException(404)` si introuvable."""
    from fastapi import HTTPException
    crop = db.query(models.Crop).filter(models.Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Culture introuvable")
    return crop


def _raise_service_error(result: dict, status_code: int = 400):
    """Lève une `HTTPException` si le résultat du service indique une erreur."""
    from fastapi import HTTPException
    if isinstance(result, dict):
        if result.get("error"):
            raise HTTPException(status_code=status_code, detail=result["error"])
        if result.get("success") is False:
            raise HTTPException(status_code=status_code, detail=result.get("error", "Opération échouée"))

def _send_email_smtp(to_email: str, subject: str, content: str):
    """Fonction utilitaire pour envoyer des e-mails via SMTP."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("EMAIL_FROM", "no-reply@agro-smart.com")

    if not all([smtp_host, smtp_user, smtp_password]):
        print(f"[INFO] Email prêt pour {to_email}, mais la configuration SMTP est manquante. Contenu:\n{content}")
        return

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(content)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        print(f"[INFO] Email envoyé avec succès à {to_email}")
    except (smtplib.SMTPException, gaierror, ConnectionRefusedError) as exc:
        print(f"[ERROR] Échec de l'envoi de l'email à {to_email}: {exc}")
    except Exception as exc:
        # Catcher les autres erreurs inattendues
        print(f"[ERROR] Erreur inattendue lors de l'envoi de l'email à {to_email}: {exc}")


def send_validation_email(user: models.User):
    """Envoie un email de validation à l'utilisateur"""
    subject = "Votre compte AgroSmart a été validé"
    content = f"""Bonjour {user.full_name},

Votre compte AgroSmart a été validé par l'administrateur.
Vous pouvez maintenant vous connecter et accéder à votre tableau de bord.

Email: {user.email}
Type de compte: {user.account_type}

Merci,
L'équipe AgroSmart
"""

    _send_email_smtp(user.email, subject, content)


def send_password_reset_email(user: models.User, token: str):
    """Envoie un email de réinitialisation de mot de passe."""
    reset_url = os.getenv("PASSWORD_RESET_URL", f"https://app.agro-smart.com/reset-password?token={token}")

    subject = "Réinitialisation du mot de passe AgroSmart"
    content = f"""Bonjour {user.full_name},

Vous avez demandé une réinitialisation du mot de passe pour votre compte AgroSmart.
Cliquez sur le lien suivant pour définir un nouveau mot de passe :

{reset_url}

Ce lien expire dans 1 heure.
Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Merci,
L'équipe AgroSmart
"""

    _send_email_smtp(user.email, subject, content)


def create_default_admin_if_missing():
    """Crée l'admin par défaut si manquant"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@agro-smart.com").strip().lower()
        admin = db.query(models.User).filter(models.User.email == admin_email).first()
        if not admin:
            from auth import get_password_hash
            admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
            if not admin_password:
                print("[WARNING] Le mot de passe de l'admin par défaut n'est pas défini. L'admin ne sera pas créé.")
                return
            admin = models.User(
                full_name="Administrateur Agro Smart",
                email=admin_email,
                username=admin_email.split("@", 1)[0],
                hashed_password=get_password_hash(admin_password),
                region="Siège",
                total_surface=0.0,
                role="admin",
                is_admin=True,
                is_validated=True,
                is_active=True,
                account_type="admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[OK] Compte administrateur créé: {admin_email}")
    finally:
        db.close()


def create_sample_data():
    """Fonction désactivée pour éviter la création de données d'exemple."""
    print("[WARNING] create_sample_data() est désactivé. Aucune donnée factice ne sera insérée.")
    return