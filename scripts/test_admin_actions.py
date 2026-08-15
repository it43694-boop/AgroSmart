import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import SessionLocal
import models
from auth import get_password_hash
from fastapi.testclient import TestClient
import main

DB = SessionLocal()

admin_email = 'AgroSmart@gmail.com'
admin_password = 'Admin123!'
admin_code = 'Ibrahim200119!'

victim_email = 'victim_test@agro.com'

# create victim user
victim = DB.query(models.User).filter(models.User.email == victim_email).first()
if not victim:
    victim = models.User(
        email=victim_email,
        full_name='Victim Test',
        phone='000',
        region='Test',
        total_surface=0.0,
        hashed_password=get_password_hash('Victim123!'),
        role='farmer',
        account_type='farmer',
        is_admin=False,
        is_validated=True,
        is_active=True,
    )
    DB.add(victim)
    DB.commit()
    DB.refresh(victim)
    print('Created victim user id=', victim.id)
else:
    print('Victim exists id=', victim.id)

client = TestClient(main.app)

print('\n--- Attempt login with admin password ---')
resp = client.post('/token', data={'username': admin_email, 'password': admin_password})
print('status', resp.status_code, 'json', resp.json())

access = None
if resp.status_code == 200:
    access = resp.json().get('access_token')

if access:
    headers = {'Authorization': f'Bearer {access}'}
    print('\n--- Attempt DELETE user with admin JWT ---')
    r = client.delete(f'/admin/users/{victim.id}/', headers=headers)
    print('DELETE status', r.status_code, 'body', r.json() if r.content else '')
else:
    print('No access token from password login')

print('\n--- Attempt login with admin_code ---')
resp2 = client.post('/token', data={'username': admin_email, 'admin_code': admin_code})
print('status', resp2.status_code, 'json', resp2.json())

access2 = None
if resp2.status_code == 200:
    access2 = resp2.json().get('access_token')

if access2:
    headers2 = {'Authorization': f'Bearer {access2}'}
    print('\n--- Attempt DELETE user with admin_code JWT ---')
    r2 = client.delete(f'/admin/users/{victim.id}/', headers=headers2)
    print('DELETE status', r2.status_code, 'body', r2.json() if r2.content else '')
else:
    print('No access token from admin_code login')

# cleanup: try to remove victim if still exists
v = DB.query(models.User).filter(models.User.email == victim_email).first()
if v:
    DB.delete(v)
    DB.commit()
    print('Cleaned up victim')

DB.close()
