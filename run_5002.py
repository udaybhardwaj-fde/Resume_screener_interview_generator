import os

from app import app


if __name__ == '__main__':
    os.environ.setdefault('PORT', '5002')
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', host='127.0.0.1', port=5002)
