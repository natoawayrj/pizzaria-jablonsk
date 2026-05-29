import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from .db import query_one, execute

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if 'cliente_id' not in session:
            flash('Faça login para continuar.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return wrapped


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'cliente_id' in session:
        return redirect(url_for('cardapio.index'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']

        cliente = query_one(
            "SELECT id, nome, senha_hash FROM clientes WHERE email=:e AND ativo=1",
            {'e': email}
        )
        if cliente and check_password_hash(cliente['senha_hash'], senha):
            session['cliente_id']   = cliente['id']
            session['cliente_nome'] = cliente['nome']
            flash(f'Bem-vindo, {cliente["nome"].split()[0]}!', 'success')
            return redirect(request.args.get('next') or url_for('cardapio.index'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if 'cliente_id' in session:
        return redirect(url_for('cardapio.index'))

    if request.method == 'POST':
        nome     = request.form['nome'].strip()
        email    = request.form['email'].strip().lower()
        senha    = request.form['senha']
        telefone = request.form.get('telefone', '').strip() or None

        if query_one("SELECT id FROM clientes WHERE email=:e", {'e': email}):
            flash('E-mail já cadastrado.', 'danger')
            return render_template('auth/cadastro.html')

        cliente_id = execute(
            "INSERT INTO clientes (nome, email, senha_hash, telefone, ativo) VALUES (:n,:e,:s,:t,1)",
            {'n': nome, 'e': email, 's': generate_password_hash(senha), 't': telefone}
        )
        session['cliente_id']   = cliente_id
        session['cliente_nome'] = nome
        flash('Conta criada! Adicione um endereço de entrega.', 'success')
        return redirect(url_for('pedido.adicionar_endereco', next=url_for('cardapio.cardapio')))

    return render_template('auth/cadastro.html')


@auth_bp.route('/logout')
def logout():
    session.pop('cliente_id',   None)
    session.pop('cliente_nome', None)
    flash('Você saiu da conta.', 'info')
    return redirect(url_for('auth.login'))
