import base64
import secrets
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports like `database` and `models` work
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database import SessionLocal
import models


def generate_secret():
    # 10 random bytes -> base32 (no padding)
    return base64.b32encode(secrets.token_bytes(10)).decode('utf-8').replace('=', '')


def generate_backup_codes(n=10):
    return ','.join(secrets.token_hex(4) for _ in range(n))


if __name__ == '__main__':
    session = SessionLocal()
    try:
        # target roles
        roles = ['admin', 'bank', 'insurance']
        users = session.query(models.User).filter(
            (models.User.role.in_(roles)) | (models.User.is_admin == True)
        ).all()
        updated = []
        for u in users:
            changed = False
            if not u.mfa_enabled:
                u.mfa_secret = generate_secret()
                u.mfa_backup_codes = generate_backup_codes(10)
                u.mfa_enabled = True
                changed = True
            else:
                # still ensure secret/backup exist
                if not u.mfa_secret:
                    u.mfa_secret = generate_secret()
                    changed = True
                if not u.mfa_backup_codes:
                    u.mfa_backup_codes = generate_backup_codes(10)
                    changed = True
            if changed:
                session.add(u)
                updated.append({'id': u.id, 'email': u.email})
        session.commit()
        print(json.dumps({'updated': updated}))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
    finally:
        session.close()
