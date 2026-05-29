#!/usr/bin/env python3
"""
init_sqlite.py — Cria banco SQLite e popula dados estáticos.
Uso: python scripts/init_sqlite.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///pizzaria.db')
engine = create_engine(DB_URL)

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    senha_hash    TEXT    NOT NULL,
    perfil        TEXT    NOT NULL DEFAULT 'atendente',
    ativo         INTEGER NOT NULL DEFAULT 1,
    ultimo_acesso TEXT    NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    senha_hash      TEXT    NOT NULL,
    telefone        TEXT    NULL,
    data_nascimento TEXT    NULL,
    ativo           INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enderecos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id   INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    logradouro   TEXT    NOT NULL,
    numero       TEXT    NOT NULL,
    complemento  TEXT    NULL,
    bairro       TEXT    NOT NULL,
    cidade       TEXT    NOT NULL DEFAULT 'Niterói',
    estado       TEXT    NOT NULL DEFAULT 'RJ',
    cep          TEXT    NOT NULL,
    principal    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categorias (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL,
    tipo       TEXT    NOT NULL,
    ativo      INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS massas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    descricao       TEXT    NULL,
    preco_adicional REAL    NOT NULL DEFAULT 0.00,
    ativo           INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bordas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    descricao       TEXT    NULL,
    preco_adicional REAL    NOT NULL DEFAULT 0.00,
    ativo           INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sabores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL,
    descricao    TEXT    NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    preco_base   REAL    NOT NULL,
    disponivel   INTEGER NOT NULL DEFAULT 1,
    imagem_url   TEXT    NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS produtos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL,
    descricao    TEXT    NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    preco        REAL    NOT NULL,
    estoque      INTEGER NOT NULL DEFAULT 0,
    disponivel   INTEGER NOT NULL DEFAULT 1,
    imagem_url   TEXT    NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cupons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT    NOT NULL UNIQUE,
    tipo            TEXT    NOT NULL,
    valor           REAL    NOT NULL,
    valor_minimo    REAL    NOT NULL DEFAULT 0.00,
    validade        TEXT    NULL,
    usos_maximos    INTEGER NULL,
    usos_realizados INTEGER NOT NULL DEFAULT 0,
    ativo           INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pedidos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id),
    endereco_id         INTEGER NOT NULL REFERENCES enderecos(id),
    cupom_id            INTEGER NULL     REFERENCES cupons(id),
    status              TEXT    NOT NULL DEFAULT 'recebido',
    recebido_em         TEXT    NULL,
    em_producao_em      TEXT    NULL,
    saiu_entrega_em     TEXT    NULL,
    entregue_em         TEXT    NULL,
    cancelado_em        TEXT    NULL,
    subtotal            REAL    NOT NULL,
    desconto            REAL    NOT NULL DEFAULT 0.00,
    total               REAL    NOT NULL,
    forma_pagamento     TEXT    NOT NULL DEFAULT 'pendente',
    troco_para          REAL    NULL,
    observacao          TEXT    NULL,
    cancelamento_motivo TEXT    NULL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL,
    massa_id        INTEGER NULL REFERENCES massas(id),
    borda_id        INTEGER NULL REFERENCES bordas(id),
    produto_id      INTEGER NULL REFERENCES produtos(id),
    quantidade      INTEGER NOT NULL DEFAULT 1,
    preco_unitario  REAL    NOT NULL,
    subtotal        REAL    NOT NULL,
    observacao      TEXT    NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens_pedido_sabores (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    item_pedido_id INTEGER NOT NULL REFERENCES itens_pedido(id) ON DELETE CASCADE,
    sabor_id       INTEGER NOT NULL REFERENCES sabores(id),
    posicao        INTEGER NOT NULL,
    UNIQUE(item_pedido_id, posicao)
);

CREATE TABLE IF NOT EXISTS avaliacoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id   INTEGER NOT NULL UNIQUE REFERENCES pedidos(id) ON DELETE CASCADE,
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nota        INTEGER NOT NULL CHECK(nota BETWEEN 1 AND 5),
    comentario  TEXT    NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS status_historico (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    status_anterior TEXT    NULL,
    status_novo     TEXT    NOT NULL,
    admin_id        INTEGER NULL REFERENCES admin_usuarios(id),
    observacao      TEXT    NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

SEED = """
INSERT OR IGNORE INTO categorias (id, nome, tipo) VALUES
    (1, 'Tradicionais', 'pizza'),
    (2, 'Especiais',    'pizza'),
    (3, 'Doces',        'pizza'),
    (4, 'Bebidas',      'produto'),
    (5, 'Sobremesas',   'produto'),
    (6, 'Porções',      'produto');

INSERT OR IGNORE INTO massas (id, nome, descricao, preco_adicional) VALUES
    (1, 'Fina',        'Massa crocante e levinha',                     0.00),
    (2, 'Tradicional', 'Massa clássica no estilo italiano',            0.00),
    (3, 'Grossa',      'Massa alta e macia, estilo americano',         3.00),
    (4, 'Integral',    'Massa integral com farinha de trigo integral', 5.00);

INSERT OR IGNORE INTO bordas (id, nome, descricao, preco_adicional) VALUES
    (1, 'Sem borda',    'Sem recheio na borda',                 0.00),
    (2, 'Catupiry',     'Borda recheada com Catupiry cremoso',  6.00),
    (3, 'Cheddar',      'Borda recheada com cheddar derretido', 6.00),
    (4, 'Chocolate',    'Borda recheada com chocolate ao leite',6.00),
    (5, 'Cream Cheese', 'Borda recheada com cream cheese',      7.00);

INSERT OR IGNORE INTO sabores (id, nome, descricao, categoria_id, preco_base, disponivel) VALUES
    (1,  'Margherita',            'Molho de tomate, mussarela fresca e manjericão',         1, 39.90, 1),
    (2,  'Calabresa',             'Calabresa fatiada, cebola, azeitona e mussarela',        1, 42.90, 1),
    (3,  'Portuguesa',            'Presunto, ovo, cebola, azeitona e pimentão',             1, 44.90, 1),
    (4,  'Mussarela',             'Mussarela especial, orégano e molho de tomate',          1, 38.90, 1),
    (5,  'Frango com Catupiry',   'Frango desfiado temperado com Catupiry cremoso',         1, 46.90, 1),
    (6,  'Napolitana',            'Tomate fresco, mussarela, manjericão e alho',            1, 41.90, 1),
    (7,  'Quatro Queijos',        'Mussarela, parmesão, gorgonzola e provolone',            2, 54.90, 1),
    (8,  'Pepperoni',             'Generosa camada de pepperoni com mussarela especial',    2, 52.90, 1),
    (9,  'Carne Seca',            'Carne seca desfiada, catupiry e cebola caramelizada',    2, 56.90, 1),
    (10, 'Camarão',               'Camarão salteado, catupiry e requeijão',                 2, 64.90, 1),
    (11, 'Costela BBQ',           'Costela desfiada, molho barbecue e cebola crispy',       2, 58.90, 1),
    (12, 'Chocolate com Morango', 'Chocolate ao leite derretido com morangos frescos',      3, 48.90, 1),
    (13, 'Nutella com Banana',    'Nutella generosa com bananas caramelizadas',             3, 52.90, 1),
    (14, 'Prestígio',             'Chocolate com coco ralado e leite condensado',           3, 46.90, 1),
    (15, 'Romeu e Julieta',       'Requeijão cremoso com goiabada',                         3, 44.90, 1);

INSERT OR IGNORE INTO produtos (id, nome, descricao, categoria_id, preco, estoque, disponivel) VALUES
    (1, 'Coca-Cola 2L',          'Refrigerante Coca-Cola 2 litros',            4, 12.00, 999, 1),
    (2, 'Coca-Cola Lata 350ml',  'Refrigerante Coca-Cola lata gelada',         4,  6.00, 999, 1),
    (3, 'Guaraná Antarctica 2L', 'Refrigerante Guaraná Antarctica 2 litros',   4, 10.00, 999, 1),
    (4, 'Água Mineral 500ml',    'Água mineral sem gás',                       4,  4.00, 999, 1),
    (5, 'Suco de Laranja 500ml', 'Suco natural de laranja',                    4,  9.00,  50, 1),
    (6, 'Petit Gateau',          'Bolinho de chocolate quente com sorvete',    5, 18.00,  20, 1),
    (7, 'Brownie com Sorvete',   'Brownie caseiro com sorvete de baunilha',    5, 16.00,  20, 1),
    (8, 'Batata Frita Grande',   'Batata frita crocante, porção grande',       6, 22.00, 999, 1),
    (9, 'Frango Frito',          'Pedaços de frango empanado e frito',         6, 28.00, 999, 1);

UPDATE sabores SET imagem_url = '/static/img/margherita.jpg'        WHERE id = 1;
UPDATE sabores SET imagem_url = '/static/img/calabresa.jpg'          WHERE id = 2;
UPDATE sabores SET imagem_url = '/static/img/portuguesa.jpg'         WHERE id = 3;
UPDATE sabores SET imagem_url = '/static/img/mussarela.jpg'          WHERE id = 4;
UPDATE sabores SET imagem_url = '/static/img/frango_comCatupiry.jpg' WHERE id = 5;
UPDATE sabores SET imagem_url = '/static/img/napolitana.jpg'         WHERE id = 6;
UPDATE sabores SET imagem_url = '/static/img/4queijos.jpg'           WHERE id = 7;
UPDATE sabores SET imagem_url = '/static/img/pepperoni.jpg'          WHERE id = 8;
UPDATE sabores SET imagem_url = '/static/img/carne_seca.jpg'         WHERE id = 9;
UPDATE sabores SET imagem_url = '/static/img/camarao.jpg'            WHERE id = 10;
UPDATE sabores SET imagem_url = '/static/img/Costela.jpg'            WHERE id = 11;
UPDATE sabores SET imagem_url = '/static/img/chocolate_com_morango.jpg' WHERE id = 12;
UPDATE sabores SET imagem_url = '/static/img/nutella_com_banana.jpg' WHERE id = 13;
UPDATE sabores SET imagem_url = '/static/img/prestigio.jpg'          WHERE id = 14;
UPDATE sabores SET imagem_url = '/static/img/romeu_e_julieta.jpg'    WHERE id = 15;

UPDATE produtos SET imagem_url = '/static/img/colca_2l.jpg'          WHERE id = 1;
UPDATE produtos SET imagem_url = '/static/img/coca_350.jpg'          WHERE id = 2;
UPDATE produtos SET imagem_url = '/static/img/guarana.jpg'           WHERE id = 3;
UPDATE produtos SET imagem_url = '/static/img/agua.jpg'              WHERE id = 4;
UPDATE produtos SET imagem_url = '/static/img/suco_de_laranja.jpg'   WHERE id = 5;
UPDATE produtos SET imagem_url = '/static/img/Petit_Gateau.jpg'      WHERE id = 6;
UPDATE produtos SET imagem_url = '/static/img/Brownie_com_Sorvete.jpg' WHERE id = 7;
UPDATE produtos SET imagem_url = '/static/img/Batata.jpg'            WHERE id = 8;
UPDATE produtos SET imagem_url = '/static/img/frango_frito.jpg'      WHERE id = 9;

INSERT OR IGNORE INTO cupons (codigo, tipo, valor, valor_minimo, validade, usos_maximos, ativo) VALUES
    ('BEMVINDO10',   'percentual', 10.00,   0.00, date('now', '+180 days'), 200, 1),
    ('FIDELIDADE15', 'percentual', 15.00,  80.00, date('now', '+180 days'), 150, 1),
    ('PROMO20',      'fixo',       20.00, 100.00, date('now', '+180 days'), 100, 1),
    ('ANIVERSARIO',  'percentual', 20.00,   0.00, date('now', '+180 days'),  50, 1),
    ('PRIMEIRA5',    'fixo',        5.00,  40.00, date('now', '+180 days'), 500, 1);
"""

def init():
    from werkzeug.security import generate_password_hash

    with engine.begin() as conn:
        for stmt in SCHEMA.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

        for stmt in SEED.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

        existe = conn.execute(
            text("SELECT id FROM admin_usuarios WHERE email='admin@pizzariajablonsk.com.br'")
        ).fetchone()
        if not existe:
            conn.execute(text(
                "INSERT INTO admin_usuarios (nome, email, senha_hash, perfil) VALUES "
                "('Administrador', 'admin@pizzariajablonsk.com.br', :h, 'super_admin')"
            ), {'h': generate_password_hash('admin123')})

    print('Banco inicializado com sucesso.')
    print('Admin: admin@pizzariajablonsk.com.br / admin123')
    print('Troque a senha em produção via scripts/setup_admin.py')

if __name__ == '__main__':
    init()
