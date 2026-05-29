#!/usr/bin/env python3
"""
faker_seed.py — Popula a Pizzaria Jablonsk com 6 meses de dados realistas
Insere direto no MySQL via SQLAlchemy (sem CSV intermediário)

Instalação das dependências:
    pip install faker sqlalchemy pymysql

Uso:
    python faker_seed.py

Configuração:
    Ajuste DB_URL abaixo com suas credenciais do MySQL.
"""

import random
import hashlib
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import create_engine, text

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# =============================================================================
# CONFIGURAÇÃO — ajuste conforme seu ambiente
# =============================================================================
DB_URL      = os.environ['DATABASE_URL']
NUM_CLIENTES = 60
NUM_PEDIDOS  = 280
MESES        = 6
SEED         = 42
# =============================================================================

fake = Faker('pt_BR')
Faker.seed(SEED)
random.seed(SEED)


# -----------------------------------------------------------------------------
# DADOS ESTÁTICOS — cardápio e cupons
# -----------------------------------------------------------------------------

BAIRROS_NITEROI = [
    'Icaraí', 'Ingá', 'São Francisco', 'Fonseca', 'Barreto',
    'Santa Rosa', 'Charitas', 'Jurujuba', 'Vital Brazil', 'Centro',
    'Piratininga', 'Itaipu', 'Cafubá', 'Camboinhas', 'Jacaré',
]

COMENTARIOS_POR_NOTA = {
    5: ['Excelente! Pizza chegou quentinha e deliciosa!', 'Perfeito, amei cada detalhe.',
        'Voltarei com certeza. Recomendo demais!', 'Melhor pizza de Niterói!', None],
    4: ['Muito boa! Só demorou um pouquinho a mais.', 'Gostei bastante, recomendo.',
        'Pizza ótima, entrega rápida.', None],
    3: ['Mediana, esperava um pouco mais.', 'Estava ok, mas a borda veio menos quente.',
        'Razoável.', None],
    2: ['Demorou muito e a pizza veio morna.', 'Não gostei muito, esperava mais qualidade.'],
    1: ['Péssimo atendimento, pizza veio errada.', 'Chegou fria e muito atrasada.'],
}


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def gerar_datetime_realista() -> datetime:
    """
    Gera datetime aleatório nos últimos MESES meses.
    Concentra volume nos horários de pico (18h–23h) e fins de semana.
    """
    fim    = datetime.now()
    inicio = fim - timedelta(days=MESES * 30)
    dt     = inicio + timedelta(seconds=random.randint(0, int((fim - inicio).total_seconds())))

    # Pesos por hora: pico entre 18h e 22h
    pesos_hora = [1,1,1,1,1,1,1,1,2,2,2,2,3,3,3,3,4,6,9,11,11,9,6,3]
    hora = random.choices(range(24), weights=pesos_hora, k=1)[0]

    # Fins de semana têm 40% mais pedidos (ajuste de dia mantido pelo datetime aleatório)
    return dt.replace(hour=hora, minute=random.randint(0,59),
                      second=random.randint(0,59), microsecond=0)


def calcular_sla(recebido: datetime, status: str):
    """Retorna (em_producao, saiu_entrega, entregue, cancelado) com tempos realistas."""
    em_producao  = recebido + timedelta(minutes=random.randint(3, 10))
    saiu_entrega = em_producao + timedelta(minutes=random.randint(15, 30))
    entregue     = saiu_entrega + timedelta(minutes=random.randint(15, 45))
    cancelado    = None

    if status == 'cancelado':
        cancelado   = recebido + timedelta(minutes=random.randint(2, 15))
        em_producao = saiu_entrega = entregue = None
    elif status == 'recebido':
        em_producao = saiu_entrega = entregue = None
    elif status == 'em_producao':
        saiu_entrega = entregue = None
    elif status == 'saiu_para_entrega':
        entregue = None

    return em_producao, saiu_entrega, entregue, cancelado


# -----------------------------------------------------------------------------
# INSERÇÕES
# -----------------------------------------------------------------------------

def inserir_clientes(conn):
    cliente_ids = []
    for _ in range(NUM_CLIENTES):
        r = conn.execute(text(
            "INSERT INTO clientes (nome, email, senha_hash, telefone, data_nascimento, ativo) "
            "VALUES (:n, :e, :s, :t, :d, 1)"
        ), {
            'n': fake.name(),
            'e': fake.unique.email(),
            's': hash_senha('senha123'),
            't': f"(21) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            'd': fake.date_of_birth(minimum_age=18, maximum_age=65),
        })
        cid = r.lastrowid
        cliente_ids.append(cid)

        num_end = random.choices([1, 2], weights=[70, 30])[0]
        for i in range(num_end):
            conn.execute(text(
                "INSERT INTO enderecos "
                "(cliente_id, logradouro, numero, complemento, bairro, cidade, estado, cep, principal) "
                "VALUES (:cid, :l, :n, :comp, :b, 'Niterói', 'RJ', :cep, :p)"
            ), {
                'cid':  cid,
                'l':    f"Rua {fake.last_name()}",
                'n':    str(random.randint(1, 999)),
                'comp': random.choice([None, f'Apto {random.randint(101,999)}', None, None]),
                'b':    random.choice(BAIRROS_NITEROI),
                'cep':  f"{random.randint(24000,24999)}-{random.randint(100,999):03d}",
                'p':    1 if i == 0 else 0,
            })

    return cliente_ids


def inserir_pedidos(conn, cliente_ids):
    # Carregar preços do banco (já inseridos)
    massas   = {r[0]: float(r[1]) for r in conn.execute(text("SELECT id, preco_adicional FROM massas WHERE ativo=1"))}
    bordas   = {r[0]: float(r[1]) for r in conn.execute(text("SELECT id, preco_adicional FROM bordas WHERE ativo=1"))}
    sabores  = {r[0]: float(r[1]) for r in conn.execute(text("SELECT id, preco_base FROM sabores WHERE disponivel=1"))}
    produtos = {r[0]: float(r[1]) for r in conn.execute(text("SELECT id, preco FROM produtos WHERE disponivel=1"))}
    cupons   = conn.execute(text("SELECT id, tipo, valor, valor_minimo FROM cupons WHERE ativo=1")).fetchall()

    massa_ids  = list(massas.keys())
    borda_ids  = list(bordas.keys())
    sabor_list = list(sabores.keys())
    prod_list  = list(produtos.keys())

    STATUS_CHOICES  = ['entregue','cancelado','em_producao','saiu_para_entrega','recebido']
    STATUS_WEIGHTS  = [82, 8, 4, 4, 2]
    FORMAS          = ['pix','cartao_credito','cartao_debito','dinheiro']
    FORMAS_WEIGHTS  = [40, 30, 20, 10]

    pedidos_criados = 0

    for _ in range(NUM_PEDIDOS):
        cliente_id = random.choice(cliente_ids)

        # Busca endereço principal
        row = conn.execute(text(
            "SELECT id FROM enderecos WHERE cliente_id=:c AND principal=1 LIMIT 1"
        ), {'c': cliente_id}).fetchone()
        if not row:
            continue
        endereco_id = row[0]

        recebido_em = gerar_datetime_realista()
        status      = random.choices(STATUS_CHOICES, weights=STATUS_WEIGHTS)[0]
        em_prod, saiu, entregue, cancelado = calcular_sla(recebido_em, status)
        forma = random.choices(FORMAS, weights=FORMAS_WEIGHTS)[0]

        # --- Montar itens do pedido ---
        itens    = []
        subtotal = 0.0

        # Pizzas (1–3)
        for _ in range(random.choices([1,2,3], weights=[55,35,10])[0]):
            massa_id  = random.choice(massa_ids)
            borda_id  = random.choice(borda_ids)
            n_sabores = random.choices([1,2,3], weights=[40,40,20])[0]
            sabores_escolhidos = random.sample(sabor_list, min(n_sabores, len(sabor_list)))

            # Preço = média dos sabores + adicional de massa e borda
            preco_pizza = round(
                sum(sabores[s] for s in sabores_escolhidos) / len(sabores_escolhidos)
                + massas[massa_id] + bordas[borda_id], 2
            )
            itens.append({'tipo':'pizza','massa_id':massa_id,'borda_id':borda_id,
                          'produto_id':None,'sabores':sabores_escolhidos,
                          'preco':preco_pizza,'qtd':1})
            subtotal += preco_pizza

        # Produto avulso (50% de chance)
        if prod_list and random.random() < 0.50:
            pid    = random.choice(prod_list)
            qtd_p  = random.choices([1,2], weights=[70,30])[0]
            preco_p = produtos[pid]
            itens.append({'tipo':'produto','massa_id':None,'borda_id':None,
                          'produto_id':pid,'sabores':[],'preco':preco_p,'qtd':qtd_p})
            subtotal += preco_p * qtd_p

        subtotal = round(subtotal, 2)

        # Cupom (20%)
        cupom_id = None
        desconto = 0.0
        if random.random() < 0.20:
            elegíveis = [c for c in cupons if float(c[3]) <= subtotal]
            if elegíveis:
                cup = random.choice(elegíveis)
                cupom_id = cup[0]
                desconto = round(subtotal * float(cup[2]) / 100, 2) \
                           if cup[1] == 'percentual' else float(cup[2])
                conn.execute(text(
                    "UPDATE cupons SET usos_realizados=usos_realizados+1 WHERE id=:id"
                ), {'id': cupom_id})

        total      = round(subtotal - desconto, 2)
        troco_para = round(total + random.choice([5,10,20,50]), 2) \
                     if forma == 'dinheiro' else None

        # --- Inserir pedido ---
        r = conn.execute(text("""
            INSERT INTO pedidos (
                cliente_id, endereco_id, cupom_id, status,
                recebido_em, em_producao_em, saiu_entrega_em, entregue_em, cancelado_em,
                subtotal, desconto, total, forma_pagamento, troco_para,
                created_at, updated_at
            ) VALUES (
                :cid, :eid, :cupid, :status,
                :rec, :emp, :sai, :ent, :can,
                :sub, :desc, :tot, :forma, :troco,
                :created, :updated
            )
        """), {
            'cid': cliente_id, 'eid': endereco_id, 'cupid': cupom_id, 'status': status,
            'rec': recebido_em, 'emp': em_prod, 'sai': saiu, 'ent': entregue, 'can': cancelado,
            'sub': subtotal, 'desc': desconto, 'tot': total, 'forma': forma, 'troco': troco_para,
            'created': recebido_em, 'updated': entregue or recebido_em,
        })
        pedido_id = r.lastrowid

        # --- Inserir itens ---
        for item in itens:
            r2 = conn.execute(text("""
                INSERT INTO itens_pedido
                    (pedido_id, tipo, massa_id, borda_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (:pid, :tipo, :m, :b, :p, :qtd, :preco, :sub)
            """), {'pid': pedido_id, 'tipo': item['tipo'],
                   'm': item['massa_id'], 'b': item['borda_id'], 'p': item['produto_id'],
                   'qtd': item['qtd'], 'preco': item['preco'],
                   'sub': round(item['preco'] * item['qtd'], 2)})
            item_id = r2.lastrowid

            for pos, sid in enumerate(item['sabores'], 1):
                conn.execute(text(
                    "INSERT INTO itens_pedido_sabores (item_pedido_id, sabor_id, posicao) "
                    "VALUES (:iid, :sid, :pos)"
                ), {'iid': item_id, 'sid': sid, 'pos': pos})

        # --- Avaliação (70% dos entregues) ---
        if status == 'entregue' and random.random() < 0.70:
            nota = random.choices([1,2,3,4,5], weights=[3,5,10,30,52])[0]
            conn.execute(text(
                "INSERT INTO avaliacoes (pedido_id, cliente_id, nota, comentario, created_at) "
                "VALUES (:pid, :cid, :nota, :com, :ts)"
            ), {
                'pid': pedido_id, 'cid': cliente_id, 'nota': nota,
                'com': random.choice(COMENTARIOS_POR_NOTA.get(nota, [None])),
                'ts':  entregue + timedelta(minutes=random.randint(5, 60)),
            })

        # --- Histórico de status ---
        transicoes = [('recebido', recebido_em)]
        if em_prod:    transicoes.append(('em_producao', em_prod))
        if saiu:       transicoes.append(('saiu_para_entrega', saiu))
        if entregue:   transicoes.append(('entregue', entregue))
        if cancelado:  transicoes.append(('cancelado', cancelado))

        for i, (st, ts) in enumerate(transicoes):
            conn.execute(text(
                "INSERT INTO status_historico (pedido_id, status_anterior, status_novo, created_at) "
                "VALUES (:pid, :ant, :novo, :ts)"
            ), {'pid': pedido_id, 'ant': transicoes[i-1][0] if i > 0 else None, 'novo': st, 'ts': ts})

        pedidos_criados += 1

    return pedidos_criados


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Pizzaria Jablonsk — Seed de Dados")
    print("=" * 60)
    print(f"  Banco     : {DB_URL}")
    print(f"  Clientes  : {NUM_CLIENTES}")
    print(f"  Pedidos   : {NUM_PEDIDOS}")
    print(f"  Período   : últimos {MESES} meses")
    print("=" * 60)
    print("  Pré-requisito: schema_pizzaria.sql já executado no banco")
    print("=" * 60)

    engine = create_engine(DB_URL, echo=False)

    with engine.begin() as conn:
        print(f"\n[1/2] Inserindo {NUM_CLIENTES} clientes com endereços...", end=' ', flush=True)
        cliente_ids = inserir_clientes(conn)
        print(f"OK ({len(cliente_ids)} clientes)")

        print(f"[2/2] Gerando {NUM_PEDIDOS} pedidos com itens, avaliações e histórico...", end=' ', flush=True)
        total = inserir_pedidos(conn, cliente_ids)
        print(f"OK ({total} pedidos)")

    print("\n" + "=" * 60)
    print("  Seed concluído com sucesso!")
    print("  Próximo passo: abrir o Jupyter Notebook e conectar via SQLAlchemy.")
    print("=" * 60)


if __name__ == '__main__':
    main()
