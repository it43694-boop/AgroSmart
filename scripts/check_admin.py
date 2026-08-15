import sqlite3, json, os, sys

db = os.getenv('DATABASE_URL_PATH', os.getenv('DATABASE_PATH', 'agro_smart.db'))
# if DATABASE_URL env var is set to sqlite:///..., try to extract filename
env_db = os.getenv('DATABASE_URL')
if env_db and env_db.startswith('sqlite:///'):
    db = env_db.replace('sqlite:///', '')

result = {'db_path': db}

if not os.path.exists(db):
    result['error'] = 'db_file_not_found'
    print(json.dumps(result))
    sys.exit(0)

try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Try to select admins by role or is_admin flag
    cur.execute("SELECT id, email, role, is_admin, mfa_enabled, created_at FROM users WHERE role=? OR is_admin=1", ('admin',))
    rows = cur.fetchall()
    admins = []
    for r in rows:
        admins.append({
            'id': r[0],
            'email': r[1],
            'role': r[2],
            'is_admin': bool(r[3]),
            'mfa_enabled': bool(r[4]),
            'created_at': r[5]
        })
    result['admins'] = admins
    print(json.dumps(result))
except Exception as e:
    result['error'] = str(e)
    print(json.dumps(result))
    sys.exit(1)
finally:
    try:
        conn.close()
    except Exception:
        pass
