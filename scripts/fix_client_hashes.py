#!/usr/bin/env python3
"""
fix_client_hashes.py — Corrige hashes legados (sha256) dos clientes do seed.

Os clientes inseridos pela versão antiga do faker_seed.py usavam sha256,
incompatível com check_password_hash (werkzeug) do login. Este script
reescreve o hash para o formato werkzeug SEM apagar nenhum dado — não
afeta o BI (a coluna senha_hash não vai pros CSVs/views).

Todos os clientes do seed passam a ter a senha: senha123

Uso: python scripts/fix_client_hashes.py
"""
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.environ['DATABASE_URL']
engine = create_engine(DB_URL)

SENHA_PADRAO = 'senha123'

with engine.begin() as conn:
    # Hash werkzeug começa com 'pbkdf2:' ou 'scrypt:'. Atualiza só os que NÃO têm.
    rows = conn.execute(text(
        "UPDATE clientes "
        "SET senha_hash = :h "
        "WHERE senha_hash NOT LIKE 'pbkdf2:%' AND senha_hash NOT LIKE 'scrypt:%'"
    ), {'h': generate_password_hash(SENHA_PADRAO)})
    print(f"OK — {rows.rowcount} clientes atualizados. Senha: {SENHA_PADRAO}")
