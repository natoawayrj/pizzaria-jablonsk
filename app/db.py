import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from dotenv import load_dotenv

load_dotenv()
DB_URL    = os.environ['DATABASE_URL']
IS_SQLITE = DB_URL.startswith('sqlite')
_engine   = create_engine(DB_URL, pool_pre_ping=True)


def group_concat(expr, order_by, sep=' + '):
    """GROUP_CONCAT portável MySQL/SQLite (sintaxes incompatíveis: SEPARATOR vs vírgula)."""
    if IS_SQLITE:
        return f"GROUP_CONCAT({expr}, '{sep}')"
    return f"GROUP_CONCAT({expr} ORDER BY {order_by} SEPARATOR '{sep}')"


def ano_mes(col):
    """Extrai 'YYYY-MM' de uma coluna de data — portável MySQL/SQLite."""
    if IS_SQLITE:
        return f"strftime('%Y-%m', {col})"
    return f"DATE_FORMAT({col}, '%Y-%m')"


# SQLite não aplica FK por padrão — liga em toda conexão
if DB_URL.startswith('sqlite'):
    @event.listens_for(_engine, 'connect')
    def _enable_sqlite_fk(dbapi_conn, _record):
        dbapi_conn.execute('PRAGMA foreign_keys=ON')


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


@contextmanager
def transaction():
    """Agrupa múltiplos statements numa transação única (tudo ou nada)."""
    with _engine.begin() as conn:
        yield conn


def tx_execute(conn, sql, params=None):
    """execute() dentro de uma transação aberta. Retorna lastrowid."""
    return conn.execute(text(sql), params or {}).lastrowid
