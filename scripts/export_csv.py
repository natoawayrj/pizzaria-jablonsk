#!/usr/bin/env python3
"""
export_csv.py — Exporta tabelas e views do banco para CSV (Power BI)
Uso: python export_csv.py
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL  = os.environ['DATABASE_URL']
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
os.makedirs(OUT_DIR, exist_ok=True)

engine = create_engine(DB_URL)

def export(nome, sql):
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    # Converte colunas de minutos para int (evita "59.0" → locale bug no Power BI)
    min_cols = [c for c in df.columns if c.startswith('min_')]
    for c in min_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')
    path = os.path.join(OUT_DIR, f'{nome}.csv')
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  {nome}.csv — {len(df)} linhas')
    return df

print('=' * 50)
print('  Pizzaria Jablonsk — Export CSV para Power BI')
print('=' * 50)

# ── FATO PRINCIPAL ────────────────────────────────────
export('fato_pedidos', "SELECT * FROM fato_pedidos")

# ── DIMENSÕES ─────────────────────────────────────────
export('dim_clientes', "SELECT * FROM dim_clientes")
export('dim_produtos', "SELECT * FROM dim_produtos")

export('dim_massas', """
    SELECT id AS massa_id, nome, descricao, preco_adicional, ativo
    FROM massas
""")

export('dim_bordas', """
    SELECT id AS borda_id, nome, descricao, preco_adicional, ativo
    FROM bordas
""")

export('dim_cupons', """
    SELECT id AS cupom_id, codigo, tipo, valor, valor_minimo,
           validade, usos_maximos, usos_realizados, ativo
    FROM cupons
""")

# ── ITENS COM SABORES (tabela bridge desnormalizada) ───
export('itens_pedido_detalhado', """
    SELECT
        ip.id            AS item_id,
        ip.pedido_id,
        ip.tipo,
        ip.quantidade,
        ip.preco_unitario,
        ip.subtotal,
        m.nome           AS massa,
        b.nome           AS borda,
        p.nome           AS produto,
        GROUP_CONCAT(s.nome ORDER BY ips.posicao SEPARATOR ' + ') AS sabores
    FROM itens_pedido ip
    LEFT JOIN massas   m   ON m.id  = ip.massa_id
    LEFT JOIN bordas   b   ON b.id  = ip.borda_id
    LEFT JOIN produtos p   ON p.id  = ip.produto_id
    LEFT JOIN itens_pedido_sabores ips ON ips.item_pedido_id = ip.id
    LEFT JOIN sabores  s   ON s.id  = ips.sabor_id
    GROUP BY ip.id, ip.pedido_id, ip.tipo, ip.quantidade,
             ip.preco_unitario, ip.subtotal, m.nome, b.nome, p.nome
""")

# ── SABORES POR ITEM (bridge normalizada para Power BI) ─
export('bridge_itens_sabores', """
    SELECT
        ips.item_pedido_id,
        ips.posicao,
        s.id   AS sabor_id,
        s.nome AS sabor,
        cat.nome AS categoria
    FROM itens_pedido_sabores ips
    JOIN sabores    s   ON s.id   = ips.sabor_id
    JOIN categorias cat ON cat.id = s.categoria_id
""")

# ── AVALIAÇÕES ────────────────────────────────────────
export('avaliacoes', """
    SELECT
        a.id, a.pedido_id, a.cliente_id,
        a.nota, a.comentario, a.created_at,
        CASE WHEN a.nota >= 4 THEN 'Promotor'
             WHEN a.nota = 3  THEN 'Neutro'
             ELSE 'Detrator' END AS categoria_nps
    FROM avaliacoes a
""")

# ── HISTÓRICO DE STATUS ───────────────────────────────
export('status_historico', """
    SELECT
        sh.id, sh.pedido_id,
        sh.status_anterior, sh.status_novo,
        sh.created_at,
        TIMESTAMPDIFF(MINUTE,
            LAG(sh.created_at) OVER (PARTITION BY sh.pedido_id ORDER BY sh.created_at),
            sh.created_at
        ) AS minutos_desde_status_anterior
    FROM status_historico sh
""")

print('=' * 50)
print(f'  CSVs salvos em: {OUT_DIR}')
print('  Próximo passo: abrir Power BI e importar a pasta csv/')
print('=' * 50)
