import os
import sqlite3
from flask import Flask
from flask_login import LoginManager

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-lokal'),
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

@app.template_filter('waktu_relatif')
def format_waktu_relatif(value):
    if value is None:
        return ''

    from datetime import datetime

    try:
        if hasattr(value, 'strftime'):
            dt = value
        else:
            s = str(value)
            dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(value)[:10]

    now = datetime.now()
    diff = now - dt
    detik = diff.total_seconds()

    if detik < 60:
        return 'Baru saja'
    elif detik < 3600:
        menit = int(detik // 60)
        return f'{menit} menit yang lalu'
    elif detik < 86400:
        jam = int(detik // 3600)
        return f'{jam} jam yang lalu'
    elif detik < 604800:
        hari = int(detik // 86400)
        return f'{hari} hari yang lalu'
    else:
        return dt.strftime('%d %b %Y')

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
