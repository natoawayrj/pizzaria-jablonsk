from flask import Blueprint, render_template
from .db import query_all

cardapio_bp = Blueprint('cardapio', __name__)


@cardapio_bp.route('/')
def index():
    destaques = query_all("""
        SELECT s.id, s.nome, s.descricao, s.preco_base, s.imagem_url, cat.nome AS categoria
        FROM sabores s
        JOIN categorias cat ON cat.id = s.categoria_id
        WHERE s.disponivel = 1
        ORDER BY s.preco_base DESC
        LIMIT 6
    """)
    return render_template('index.html', destaques=destaques)


@cardapio_bp.route('/cardapio')
def cardapio():
    categorias_pizza = query_all(
        "SELECT id, nome FROM categorias WHERE tipo='pizza' AND ativo=1 ORDER BY id"
    )
    sabores = query_all("""
        SELECT s.id, s.nome, s.descricao, s.preco_base, s.imagem_url, s.categoria_id,
               cat.nome AS categoria
        FROM sabores s
        JOIN categorias cat ON cat.id = s.categoria_id
        WHERE s.disponivel = 1
        ORDER BY cat.id, s.nome
    """)
    categorias_prod = query_all(
        "SELECT id, nome FROM categorias WHERE tipo='produto' AND ativo=1 ORDER BY id"
    )
    produtos = query_all("""
        SELECT p.id, p.nome, p.descricao, p.preco, p.imagem_url, p.categoria_id,
               cat.nome AS categoria
        FROM produtos p
        JOIN categorias cat ON cat.id = p.categoria_id
        WHERE p.disponivel = 1
        ORDER BY cat.id, p.nome
    """)
    return render_template('cardapio.html',
                           categorias_pizza=categorias_pizza,
                           sabores=sabores,
                           categorias_prod=categorias_prod,
                           produtos=produtos)


@cardapio_bp.route('/monte-pizza')
def monte_pizza():
    massas  = query_all("SELECT id, nome, descricao, preco_adicional FROM massas  WHERE ativo=1")
    bordas  = query_all("SELECT id, nome, descricao, preco_adicional FROM bordas  WHERE ativo=1")
    sabores = query_all("""
        SELECT s.id, s.nome, s.preco_base, s.imagem_url, cat.nome AS categoria, s.categoria_id
        FROM sabores s
        JOIN categorias cat ON cat.id = s.categoria_id
        WHERE s.disponivel = 1
        ORDER BY cat.id, s.nome
    """)
    return render_template('monte_pizza.html', massas=massas, bordas=bordas, sabores=sabores)
