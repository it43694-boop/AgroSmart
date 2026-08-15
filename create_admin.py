from database import SessionLocal
from models import User
from auth import get_password_hash, generate_mfa_secret
from sqlalchemy import func
import datetime

db = SessionLocal()

try:
    normalized_email = 'agrosmart@gmail.com'
    existing_admins = db.query(User).filter(func.lower(User.email) == normalized_email).all()

    if existing_admins:
        # If multiple case-variant admin entries exist, keep the first one and remove any duplicates.
        admin = existing_admins[0]
        for duplicate in existing_admins[1:]:
            db.delete(duplicate)

        admin.email = normalized_email
        admin.username = (admin.username or normalized_email.split('@', 1)[0]).strip().lower()
        admin.full_name = 'Admin Test'
        admin.phone = '22366000000'
        admin.region = 'Bamako'
        admin.total_surface = 20.0
        admin.hashed_password = get_password_hash('Ibrahim200119!')
        admin.role = 'admin'
        admin.account_type = 'admin'
        admin.is_admin = True
        admin.is_validated = True
        admin.is_active = True
        admin.mfa_enabled = True
        admin.mfa_secret = admin.mfa_secret or generate_mfa_secret(admin.email)
        admin.created_at = admin.created_at or datetime.datetime.now()
        db.add(admin)
        db.commit()
        print('Admin existant mis à jour et doublons supprimés: AgroSmart@gmail.com (mot de passe réinitialisé à Ibrahim200119!)')
        print('MFA administrative activé avec secret provisionné pour le compte admin.')
    else:
        admin = User(
            email=normalized_email,
            full_name='Admin Test',
            phone='22366000000',
            region='Bamako',
            total_surface=20.0,
            hashed_password=get_password_hash('Ibrahim200119!'),
            role='admin',
            account_type='admin',
            is_admin=True,
            is_validated=True,
            is_active=True,
            mfa_enabled=True,
            mfa_secret=generate_mfa_secret(normalized_email),
            created_at=datetime.datetime.now()
        )
        db.add(admin)
        db.commit()
        print('✅ Admin créé: AgroSmart@gmail.com / Ibrahim200119!')
        print('MFA administrative activé avec secret provisionné pour le compte admin.')
finally:
    db.close()
