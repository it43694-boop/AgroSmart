import os
import sys
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

with SessionLocal() as db:
    u = db.query(models.User).filter(models.User.email == 'agrosmart@gmail.com').first()
    print('admin found', bool(u))
    if u:
        print('email', u.email)
        print('mfa_enabled', getattr(u, 'mfa_enabled', None))
        print('mfa_secret', getattr(u, 'mfa_secret', None))
        print('is_active', getattr(u, 'is_active', None))
        print('is_validated', getattr(u, 'is_validated', None))
        try:
            import pyotp
            totp = pyotp.TOTP(u.mfa_secret).now() if getattr(u, 'mfa_secret', None) else 'no-secret'
            print('current_totp', totp)
        except Exception as e:
            print('pyotp error', e)
            totp = ''
        client = TestClient(app)
        resp = client.post('/api/token', data={'username': 'agrosmart@gmail.com', 'password': 'Ibrahim200119!', 'mfa_code': totp})
        print('login status', resp.status_code, resp.text)
        if resp.status_code == 200:
            token = resp.json().get('access_token')
            print('token', token)
            headers = {'Authorization': f'Bearer {token}'}
            r2 = client.get('/api/admin/stats/', headers=headers)
            print('admin/stats', r2.status_code, r2.text)
            r3 = client.get('/api/me', headers=headers)
            print('api/me', r3.status_code, r3.text)
