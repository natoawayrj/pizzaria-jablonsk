import os
import logging
from datetime import datetime
from flask import Flask
from flask_wtf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

csrf = CSRFProtect()


def _dtfmt(value, fmt='%d/%m %H:%M'):
    """Formata data vinda como datetime (MySQL) ou string ISO (SQLite)."""
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(fmt)


def create_app():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__,
                template_folder=os.path.join(root, 'templates'),
                static_folder=os.path.join(root, 'static'))

    is_prod = os.environ.get('PIZZARIA_ENV', 'development') == 'production'

    # SECRET_KEY: obrigatória em produção, fallback só em dev local
    secret = os.environ.get('SECRET_KEY')
    if not secret:
        if is_prod:
            raise RuntimeError('SECRET_KEY não definida — obrigatória em produção.')
        secret = 'pj-dev-secret-only-local'
    app.config['SECRET_KEY'] = secret

    # Hardening de cookie de sessão
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=is_prod,
    )

    # Logging básico (sem isso, 500 não deixa rastro)
    logging.basicConfig(
        level=logging.INFO if is_prod else logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Proteção CSRF global em todos os POST
    csrf.init_app(app)

    # Filtro de data portável (datetime do MySQL ou string ISO do SQLite)
    app.jinja_env.filters['dtfmt'] = _dtfmt

    from .auth     import auth_bp
    from .cardapio import cardapio_bp
    from .pedido   import pedido_bp
    from .admin    import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(cardapio_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
