import sys
import pathlib

# Ensure project root is on sys.path when running from scripts/
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import SessionLocal
from models import User

email = 'AgroSmart@gmail.com'
new_name = 'Administrateur'

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print('Admin non trouvé pour', email)
        sys.exit(1)
    user.full_name = new_name
    db.commit()
    print('Admin mis à jour:', user.email, user.full_name)
finally:
    db.close()
