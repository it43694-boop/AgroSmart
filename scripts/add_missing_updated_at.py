import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import engine
from sqlalchemy import text

tables = [
    'community_tokens',
    'cooperatives',
    'cooperative_group_purchases',
    'marketplace_payments',
    'marketplace_orders',
    'marketplace_transactions',
]

conn = engine.connect()
try:
    for t in tables:
        try:
            res = conn.execute(text(f"PRAGMA table_info('{t}')"))
            cols = {row[1] for row in res.fetchall()}
        except Exception:
            print('Table', t, 'does not exist; skipping')
            continue
        if 'updated_at' in cols:
            print(f"{t}: updated_at exists")
        else:
            try:
                conn.execute(text(f"ALTER TABLE {t} ADD COLUMN updated_at DATETIME"))
                print(f"{t}: added updated_at")
            except Exception as e:
                print(f"{t}: failed to add updated_at: {e}")
finally:
    conn.close()
