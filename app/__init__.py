import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__,
                template_folder=os.path.join(root, 'templates'),
                static_folder=os.path.join(root, 'static'))

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pj-dev-secret-2025')

    from .auth     import auth_bp
    from .cardapio import cardapio_bp
    from .pedido   import pedido_bp
    from .admin    import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(cardapio_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
