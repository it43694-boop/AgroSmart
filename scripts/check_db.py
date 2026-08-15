import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import SessionLocal
import models

s = SessionLocal()
try:
    total_users = s.query(models.User).count()
    farmers = s.query(models.User).filter(models.User.role=='farmer').all()
    print('total_users', total_users)
    print('farmers_count', len(farmers))
    for f in farmers:
        print('farmer:', f.id, f.email, getattr(f, 'full_name', None), 'is_active', f.is_active, 'is_validated', f.is_validated)
    print('crops', s.query(models.Crop).count())
    print('finance', s.query(models.FinanceRecord).count())
    print('alerts', s.query(models.Alert).count())
    print('support', s.query(models.SupportMessage).count())
finally:
    s.close()
