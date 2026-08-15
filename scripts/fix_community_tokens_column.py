import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import engine
from sqlalchemy import text

conn = engine.connect()
try:
    res = conn.execute(text("PRAGMA table_info('community_tokens')"))
    cols = {row[1] for row in res.fetchall()}
    if 'updated_at' in cols:
        print('Column updated_at already exists in community_tokens')
    else:
        print('Adding updated_at column to community_tokens')
        conn.execute(text("ALTER TABLE community_tokens ADD COLUMN updated_at DATETIME"))
        print('Column added')
finally:
    conn.close()
