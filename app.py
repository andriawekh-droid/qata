import sqlite3
from flask import Flask
from flask_login import LoginManager

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='f9c60092dbc4b696ccef2fb2fc5cd2ab286346a28edc54bfe9b37f3c7ae48a5e',
    DATABASE=app.instance_path + '/qata.db',
)

@app.template_filter('tanggal')
def format_tanggal(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%d %b %Y')
    try:
        s = str(value)
        return s[:10]
    except Exception:
        return ''

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Silakan login terlebih dahulu.'

from auth import auth_bp, get_user_by_id
from dashboard import dashboard_bp
from public import public_bp

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(public_bp)

from database import init_db
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)