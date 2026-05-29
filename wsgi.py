import sys
import os

project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault('DATABASE_URL', f'sqlite:///{project_home}/pizzaria.db')
os.environ.setdefault('SECRET_KEY', 'troque-em-producao')

from app import create_app
application = create_app()
