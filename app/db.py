import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_URL  = os.environ['DATABASE_URL']
_engine = create_engine(DB_URL, pool_pre_ping=True)


def query_one(sql, params=None):
    with _engine.connect() as conn:
        row = conn.execute(text(sql), params or {}).fetchone()
        return dict(row._mapping) if row else None


def query_all(sql, params=None):
    with _engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).fetchall()
        return [dict(r._mapping) for r in rows]


def execute(sql, params=None):
    with _engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.lastrowid
