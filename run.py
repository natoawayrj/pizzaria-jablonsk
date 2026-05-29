import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # debug só fora de produção (Werkzeug debugger = RCE se exposto)
    debug = os.environ.get('PIZZARIA_ENV', 'development') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=5000)
