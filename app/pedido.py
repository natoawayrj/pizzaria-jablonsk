from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from .db import query_one, query_all, execute, transaction, tx_execute, group_concat
from .auth import login_required

pedido_bp = Blueprint('pedido', __name__)


# ── CARRINHO ──────────────────────────────────────────────────────────────────

@pedido_bp.route('/carrinho/adicionar', methods=['POST'])
def adicionar_ao_carrinho():
    carrinho = session.get('carrinho', [])
    tipo     = request.form.get('tipo')

    if tipo == 'pizza':
        massa_id  = int(request.form['massa_id'])
        borda_id  = int(request.form['borda_id'])
        sabor_ids = [int(x) for x in request.form.getlist('sabor_ids') if x][:3]

        if not sabor_ids:
            flash('Selecione ao menos 1 sabor.', 'warning')
            return redirect(url_for('cardapio.monte_pizza'))

        massa   = query_one("SELECT nome, preco_adicional FROM massas WHERE id=:id", {'id': massa_id})
        borda   = query_one("SELECT nome, preco_adicional FROM bordas WHERE id=:id", {'id': borda_id})
        # IN (...) com bind params nomeados (sem f-string de valores na SQL)
        placeholders = ','.join(f':s{i}' for i in range(len(sabor_ids)))
        sabor_params = {f's{i}': sid for i, sid in enumerate(sabor_ids)}
        sabores = query_all(
            f"SELECT id, nome, preco_base FROM sabores WHERE id IN ({placeholders})",
            sabor_params
        )

        # Pizza multi-sabor cobra o sabor mais caro (padrão de pizzaria)
        preco = round(
            max(float(s['preco_base']) for s in sabores)
            + float(massa['preco_adicional']) + float(borda['preco_adicional']), 2
        )
        carrinho.append({
            'tipo': 'pizza',
            'massa_id': massa_id, 'massa_nome': massa['nome'],
            'borda_id': borda_id, 'borda_nome': borda['nome'],
            'sabores': [{'id': s['id'], 'nome': s['nome']} for s in sabores],
            'preco_unitario': preco, 'quantidade': 1, 'subtotal': preco,
            'display': ' + '.join(s['nome'] for s in sabores),
        })
        flash('Pizza adicionada ao carrinho!', 'success')

    elif tipo == 'produto':
        pid      = int(request.form['produto_id'])
        qtd      = max(1, int(request.form.get('quantidade', 1)))
        produto  = query_one("SELECT id, nome, preco FROM produtos WHERE id=:id AND disponivel=1", {'id': pid})
        if produto:
            for item in carrinho:
                if item['tipo'] == 'produto' and item['produto_id'] == pid:
                    item['quantidade'] += qtd
                    item['subtotal']    = round(item['preco_unitario'] * item['quantidade'], 2)
                    break
            else:
                carrinho.append({
                    'tipo': 'produto', 'produto_id': pid,
                    'display': produto['nome'],
                    'preco_unitario': float(produto['preco']),
                    'quantidade': qtd,
                    'subtotal': round(float(produto['preco']) * qtd, 2),
                })
            flash(f'{produto["nome"]} adicionado!', 'success')

    session['carrinho'] = carrinho
    return redirect(url_for('pedido.ver_carrinho'))


@pedido_bp.route('/carrinho')
def ver_carrinho():
    carrinho = session.get('carrinho', [])
    subtotal = round(sum(i['subtotal'] for i in carrinho), 2)
    return render_template('carrinho.html', carrinho=carrinho, subtotal=subtotal)


@pedido_bp.route('/carrinho/remover/<int:idx>', methods=['POST'])
def remover_item(idx):
    carrinho = session.get('carrinho', [])
    if 0 <= idx < len(carrinho):
        carrinho.pop(idx)
        session['carrinho'] = carrinho
    return redirect(url_for('pedido.ver_carrinho'))


@pedido_bp.route('/carrinho/limpar', methods=['POST'])
def limpar_carrinho():
    session.pop('carrinho', None)
    return redirect(url_for('pedido.ver_carrinho'))


# ── CHECKOUT ──────────────────────────────────────────────────────────────────

@pedido_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    carrinho = session.get('carrinho', [])
    if not carrinho:
        flash('Carrinho vazio.', 'warning')
        return redirect(url_for('cardapio.cardapio'))

    cid       = session['cliente_id']
    enderecos = query_all(
        "SELECT id, logradouro, numero, complemento, bairro, principal FROM enderecos WHERE cliente_id=:c",
        {'c': cid}
    )
    subtotal  = round(sum(i['subtotal'] for i in carrinho), 2)

    if request.method == 'POST':
        eid          = int(request.form['endereco_id'])
        forma        = request.form['forma_pagamento']
        cupom_codigo = request.form.get('cupom', '').strip().upper()
        troco_para   = request.form.get('troco_para') or None
        observacao   = request.form.get('observacao', '').strip() or None

        cupom_id = None
        desconto = 0.0
        if cupom_codigo:
            c = query_one("""
                SELECT id, tipo, valor, valor_minimo, usos_maximos, usos_realizados
                FROM cupons WHERE codigo=:c AND ativo=1
                  AND (validade IS NULL OR validade >= :hoje)
            """, {'c': cupom_codigo, 'hoje': date.today().isoformat()})
            if c and float(c['valor_minimo']) <= subtotal:
                if c['usos_maximos'] is None or c['usos_realizados'] < c['usos_maximos']:
                    cupom_id = c['id']
                    desconto = round(subtotal * float(c['valor']) / 100, 2) \
                               if c['tipo'] == 'percentual' else float(c['valor'])
                else:
                    flash('Cupom esgotado.', 'warning')
            elif c:
                flash(f'Pedido mínimo para este cupom: R$ {float(c["valor_minimo"]):.2f}', 'warning')
            else:
                flash('Cupom inválido ou expirado.', 'danger')

        total  = round(subtotal - desconto, 2)
        troco  = float(troco_para) if troco_para and forma == 'dinheiro' else None
        agora  = datetime.now()

        # Tudo numa transação só: pedido + itens + sabores + histórico + cupom + estoque.
        # Se qualquer passo falhar, nada é gravado (sem pedido órfão/parcial).
        with transaction() as conn:
            pedido_id = tx_execute(conn, """
                INSERT INTO pedidos
                    (cliente_id, endereco_id, cupom_id, status, recebido_em,
                     subtotal, desconto, total, forma_pagamento, troco_para, observacao,
                     created_at, updated_at)
                VALUES
                    (:cid, :eid, :cupid, 'recebido', :now,
                     :sub, :desc, :tot, :forma, :troco, :obs,
                     :now, :now)
            """, {'cid': cid, 'eid': eid, 'cupid': cupom_id, 'now': agora,
                  'sub': subtotal, 'desc': desconto, 'tot': total,
                  'forma': forma, 'troco': troco, 'obs': observacao})

            for item in carrinho:
                item_id = tx_execute(conn, """
                    INSERT INTO itens_pedido
                        (pedido_id, tipo, massa_id, borda_id, produto_id,
                         quantidade, preco_unitario, subtotal)
                    VALUES (:pid,:tipo,:m,:b,:p,:qtd,:preco,:sub)
                """, {'pid': pedido_id, 'tipo': item['tipo'],
                      'm': item.get('massa_id'), 'b': item.get('borda_id'),
                      'p': item.get('produto_id'),
                      'qtd': item['quantidade'], 'preco': item['preco_unitario'],
                      'sub': item['subtotal']})

                if item['tipo'] == 'pizza':
                    for pos, s in enumerate(item['sabores'], 1):
                        tx_execute(conn,
                            "INSERT INTO itens_pedido_sabores (item_pedido_id, sabor_id, posicao) VALUES (:i,:s,:p)",
                            {'i': item_id, 's': s['id'], 'p': pos}
                        )
                elif item['tipo'] == 'produto':
                    # Baixa de estoque (não desce abaixo de zero)
                    tx_execute(conn,
                        "UPDATE produtos SET estoque = CASE WHEN estoque >= :q THEN estoque - :q ELSE 0 END "
                        "WHERE id = :p",
                        {'q': item['quantidade'], 'p': item['produto_id']}
                    )

            tx_execute(conn,
                "INSERT INTO status_historico (pedido_id, status_anterior, status_novo, created_at) "
                "VALUES (:pid, NULL, 'recebido', :now)",
                {'pid': pedido_id, 'now': agora}
            )
            if cupom_id:
                tx_execute(conn,
                    "UPDATE cupons SET usos_realizados=usos_realizados+1 WHERE id=:id",
                    {'id': cupom_id})

        session.pop('carrinho', None)
        flash('Pedido realizado com sucesso! Acompanhe o status abaixo.', 'success')
        return redirect(url_for('pedido.status_pedido', pedido_id=pedido_id))

    return render_template('checkout.html', carrinho=carrinho, enderecos=enderecos, subtotal=subtotal)


# ── STATUS / HISTÓRICO ────────────────────────────────────────────────────────

@pedido_bp.route('/pedido/<int:pedido_id>')
@login_required
def status_pedido(pedido_id):
    cid    = session['cliente_id']
    pedido = query_one("""
        SELECT p.*, e.logradouro, e.numero, e.bairro
        FROM pedidos p JOIN enderecos e ON e.id = p.endereco_id
        WHERE p.id=:pid AND p.cliente_id=:cid
    """, {'pid': pedido_id, 'cid': cid})

    if not pedido:
        flash('Pedido não encontrado.', 'danger')
        return redirect(url_for('pedido.meus_pedidos'))

    itens = query_all(f"""
        SELECT ip.tipo, ip.quantidade, ip.preco_unitario, ip.subtotal,
               m.nome AS massa, b.nome AS borda, prod.nome AS produto,
               {group_concat('s.nome', 'ips.posicao')} AS sabores
        FROM itens_pedido ip
        LEFT JOIN massas   m    ON m.id   = ip.massa_id
        LEFT JOIN bordas   b    ON b.id   = ip.borda_id
        LEFT JOIN produtos prod ON prod.id = ip.produto_id
        LEFT JOIN itens_pedido_sabores ips ON ips.item_pedido_id = ip.id
        LEFT JOIN sabores  s    ON s.id   = ips.sabor_id
        WHERE ip.pedido_id=:pid
        GROUP BY ip.id, ip.tipo, ip.quantidade, ip.preco_unitario,
                 ip.subtotal, m.nome, b.nome, prod.nome
    """, {'pid': pedido_id})

    avaliacao = query_one("SELECT nota FROM avaliacoes WHERE pedido_id=:pid", {'pid': pedido_id})
    return render_template('pedido_status.html', pedido=pedido, itens=itens, avaliacao=avaliacao)


@pedido_bp.route('/pedido/<int:pedido_id>/status-json')
@login_required
def status_json(pedido_id):
    cid    = session['cliente_id']
    pedido = query_one(
        "SELECT status FROM pedidos WHERE id=:pid AND cliente_id=:cid",
        {'pid': pedido_id, 'cid': cid}
    )
    if not pedido:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'status': pedido['status']})


@pedido_bp.route('/meus-pedidos')
@login_required
def meus_pedidos():
    cid     = session['cliente_id']
    pedidos = query_all("""
        SELECT p.id, p.status, p.total, p.forma_pagamento, p.created_at,
               COUNT(ip.id) AS qtd_itens
        FROM pedidos p
        LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
        WHERE p.cliente_id=:cid
        GROUP BY p.id, p.status, p.total, p.forma_pagamento, p.created_at
        ORDER BY p.created_at DESC
    """, {'cid': cid})
    return render_template('meus_pedidos.html', pedidos=pedidos)


# ── AVALIAÇÃO ─────────────────────────────────────────────────────────────────

@pedido_bp.route('/avaliar/<int:pedido_id>', methods=['GET', 'POST'])
@login_required
def avaliar(pedido_id):
    cid    = session['cliente_id']
    pedido = query_one(
        "SELECT id, status FROM pedidos WHERE id=:pid AND cliente_id=:cid",
        {'pid': pedido_id, 'cid': cid}
    )
    if not pedido or pedido['status'] != 'entregue':
        flash('Pedido não disponível para avaliação.', 'warning')
        return redirect(url_for('pedido.meus_pedidos'))

    if query_one("SELECT id FROM avaliacoes WHERE pedido_id=:pid", {'pid': pedido_id}):
        flash('Pedido já avaliado.', 'info')
        return redirect(url_for('pedido.status_pedido', pedido_id=pedido_id))

    if request.method == 'POST':
        execute(
            "INSERT INTO avaliacoes (pedido_id, cliente_id, nota, comentario) VALUES (:pid,:cid,:n,:c)",
            {'pid': pedido_id, 'cid': cid,
             'n': int(request.form['nota']),
             'c': request.form.get('comentario', '').strip() or None}
        )
        flash('Obrigado pela avaliação!', 'success')
        return redirect(url_for('pedido.status_pedido', pedido_id=pedido_id))

    return render_template('avaliar.html', pedido=pedido)


# ── ENDEREÇO ──────────────────────────────────────────────────────────────────

@pedido_bp.route('/endereco/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_endereco():
    cid = session['cliente_id']
    if request.method == 'POST':
        tem = query_one(
            "SELECT id FROM enderecos WHERE cliente_id=:cid AND principal=1", {'cid': cid}
        )
        execute("""
            INSERT INTO enderecos
                (cliente_id, logradouro, numero, complemento, bairro, cep, principal)
            VALUES (:cid,:l,:n,:comp,:b,:cep,:p)
        """, {
            'cid':  cid,
            'l':    request.form['logradouro'].strip(),
            'n':    request.form['numero'].strip(),
            'comp': request.form.get('complemento', '').strip() or None,
            'b':    request.form['bairro'].strip(),
            'cep':  request.form['cep'].strip(),
            'p':    0 if tem else 1,
        })
        flash('Endereço salvo!', 'success')
        return redirect(request.args.get('next') or url_for('cardapio.cardapio'))
    return render_template('endereco_form.html')
