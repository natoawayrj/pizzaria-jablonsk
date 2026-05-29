"""
Cria ou atualiza a senha do admin com hash werkzeug.
Uso: python setup_admin.py
"""
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.environ['DATABASE_URL']
engine = create_engine(DB_URL)

senha = input("Nova senha para admin@pizzariajablonsk.com.br: ").strip()
hash_ = generate_password_hash(senha)

with engine.begin() as conn:
    rows = conn.execute(text(
        "UPDATE admin_usuarios SET senha_hash=:h WHERE email='admin@pizzariajablonsk.com.br'"
    ), {'h': hash_})
    print(f"OK — {rows.rowcount} admin atualizado.")
