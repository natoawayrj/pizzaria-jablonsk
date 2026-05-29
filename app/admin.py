import functools
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import check_password_hash
from .db import query_one, query_all, execute

admin_bp = Blueprint('admin', __name__)

STATUS_FLOW = ['recebido', 'em_producao', 'saiu_para_entrega', 'entregue']


def admin_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return wrapped


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        admin = query_one(
            "SELECT id, nome, senha_hash, perfil FROM admin_usuarios WHERE email=:e AND ativo=1",
            {'e': email}
        )
        try:
            valid = admin and check_password_hash(admin['senha_hash'], senha)
        except Exception:
            valid = False

        if valid:
            session['admin_id']    = admin['id']
            session['admin_nome']  = admin['nome']
            session['admin_perfil'] = admin['perfil']
            execute("UPDATE admin_usuarios SET ultimo_acesso=:now WHERE id=:id",
                    {'now': datetime.now(), 'id': admin['id']})
            return redirect(url_for('admin.dashboard'))

        flash('Credenciais inválidas.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    session.pop('admin_perfil', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    stats = query_one("""
        SELECT
            (SELECT COUNT(*) FROM pedidos WHERE DATE(created_at) = CURDATE())           AS pedidos_hoje,
            (SELECT COUNT(*) FROM pedidos WHERE status = 'recebido')                    AS aguardando,
            (SELECT COUNT(*) FROM pedidos WHERE status = 'em_producao')                 AS em_producao,
            (SELECT COUNT(*) FROM pedidos WHERE status = 'saiu_para_entrega')           AS na_entrega,
            (SELECT ROUND(IFNULL(SUM(total),0),2)
               FROM pedidos WHERE status='entregue'
               AND DATE(created_at) = CURDATE())                                        AS fat_hoje,
            (SELECT ROUND(IFNULL(AVG(total),0),2)
               FROM pedidos WHERE status='entregue')                                    AS ticket_medio,
            (SELECT ROUND(IFNULL(AVG(nota),0),2) FROM avaliacoes)                      AS nota_media
    """)
    recentes = query_all("""
        SELECT p.id, c.nome AS cliente, p.status, p.total,
               p.forma_pagamento, p.created_at
        FROM pedidos p JOIN clientes c ON c.id = p.cliente_id
        ORDER BY p.created_at DESC LIMIT 10
    """)
    fat_mensal = query_all("""
        SELECT DATE_FORMAT(created_at,'%Y-%m') AS mes,
               ROUND(SUM(total),2) AS faturamento, COUNT(*) AS pedidos
        FROM pedidos WHERE status='entregue'
        GROUP BY mes ORDER BY mes DESC LIMIT 6
    """)
    return render_template('admin/dashboard.html',
                           stats=stats, recentes=recentes, fat_mensal=fat_mensal)


@admin_bp.route('/pedidos')
@admin_required
def pedidos():
    status_f = request.args.get('status', '')
    data_f   = request.args.get('data', '')
    where    = 'WHERE 1=1'
    params   = {}
    if status_f:
        where += ' AND p.status=:status'; params['status'] = status_f
    if data_f:
        where += ' AND DATE(p.created_at)=:data'; params['data'] = data_f

    lista = query_all(f"""
        SELECT p.id, c.nome AS cliente, p.status, p.total,
               p.forma_pagamento, p.created_at, COUNT(ip.id) AS qtd_itens
        FROM pedidos p
        JOIN clientes c ON c.id = p.cliente_id
        LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
        {where}
        GROUP BY p.id, c.nome, p.status, p.total, p.forma_pagamento, p.created_at
        ORDER BY p.created_at DESC LIMIT 200
    """, params)

    return render_template('admin/pedidos.html',
                           pedidos=lista, status_filtro=status_f, data_filtro=data_f)


@admin_bp.route('/pedido/<int:pedido_id>')
@admin_required
def pedido_detalhe(pedido_id):
    pedido = query_one("""
        SELECT p.*, c.nome AS cliente_nome, c.telefone,
               e.logradouro, e.numero, e.complemento, e.bairro, e.cep,
               cu.codigo AS cupom_codigo,
               av.nota, av.comentario AS avaliacao_comentario
        FROM pedidos p
        JOIN clientes  c  ON c.id  = p.cliente_id
        JOIN enderecos e  ON e.id  = p.endereco_id
        LEFT JOIN cupons      cu ON cu.id = p.cupom_id
        LEFT JOIN avaliacoes  av ON av.pedido_id = p.id
        WHERE p.id=:pid
    """, {'pid': pedido_id})

    if not pedido:
        flash('Pedido não encontrado.', 'danger')
        return redirect(url_for('admin.pedidos'))

    itens = query_all("""
        SELECT ip.tipo, ip.quantidade, ip.preco_unitario, ip.subtotal,
               m.nome AS massa, b.nome AS borda, prod.nome AS produto,
               GROUP_CONCAT(s.nome ORDER BY ips.posicao SEPARATOR ' + ') AS sabores
        FROM itens_pedido ip
        LEFT JOIN massas   m    ON m.id    = ip.massa_id
        LEFT JOIN bordas   b    ON b.id    = ip.borda_id
        LEFT JOIN produtos prod ON prod.id = ip.produto_id
        LEFT JOIN itens_pedido_sabores ips ON ips.item_pedido_id = ip.id
        LEFT JOIN sabores  s    ON s.id    = ips.sabor_id
        WHERE ip.pedido_id=:pid
        GROUP BY ip.id, ip.tipo, ip.quantidade, ip.preco_unitario,
                 ip.subtotal, m.nome, b.nome, prod.nome
    """, {'pid': pedido_id})

    historico = query_all(
        "SELECT status_anterior, status_novo, created_at FROM status_historico WHERE pedido_id=:pid ORDER BY created_at",
        {'pid': pedido_id}
    )
    return render_template('admin/pedido_detalhe.html',
                           pedido=pedido, itens=itens,
                           historico=historico, status_flow=STATUS_FLOW)


@admin_bp.route('/pedido/<int:pedido_id>/status', methods=['POST'])
@admin_required
def atualizar_status(pedido_id):
    pedido = query_one("SELECT status FROM pedidos WHERE id=:pid", {'pid': pedido_id})
    if not pedido:
        flash('Pedido não encontrado.', 'danger')
        return redirect(url_for('admin.pedidos'))

    novo    = request.form['status']
    ant     = pedido['status']
    agora   = datetime.now()
    aid     = session['admin_id']

    campos_ts = {'em_producao': 'em_producao_em',
                 'saiu_para_entrega': 'saiu_entrega_em',
                 'entregue': 'entregue_em',
                 'cancelado': 'cancelado_em'}
    campo = campos_ts.get(novo)

    if campo:
        execute(f"UPDATE pedidos SET status=:s, {campo}=:ts, updated_at=:ts WHERE id=:pid",
                {'s': novo, 'ts': agora, 'pid': pedido_id})
    else:
        execute("UPDATE pedidos SET status=:s, updated_at=:ts WHERE id=:pid",
                {'s': novo, 'ts': agora, 'pid': pedido_id})

    execute("""
        INSERT INTO status_historico (pedido_id, status_anterior, status_novo, admin_id, created_at)
        VALUES (:pid,:ant,:novo,:aid,:now)
    """, {'pid': pedido_id, 'ant': ant, 'novo': novo, 'aid': aid, 'now': agora})

    motivo = request.form.get('motivo', '').strip()
    if novo == 'cancelado' and motivo:
        execute("UPDATE pedidos SET cancelamento_motivo=:m WHERE id=:pid", {'m': motivo, 'pid': pedido_id})

    flash(f'Status → {novo.replace("_", " ")}.', 'success')
    return redirect(url_for('admin.pedido_detalhe', pedido_id=pedido_id))
