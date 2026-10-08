import os
import sqlite3
from flask import Flask
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, instance_relative_config=True)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-lokal'),
    DATABASE=app.instance_path + '/qata.db',
    MAX_CONTENT_LENGTH=3 * 1024 * 1024,  # Maksimal request payload 3 MB
)

@app.after_request
def set_security_headers(response):
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-XSS-Protection', '1; mode=block')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    # CSP: 'unsafe-inline' dipertahankan untuk script/style karena template
    # kemungkinan memakai inline; perketat dengan nonce bila sudah dimigrasi.
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'")
    return response

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

@app.context_processor
def inject_page_theme():
    # Default untuk halaman yang tidak override page_theme secara eksplisit
    # (dashboard user sendiri, landing page, dsb).
    # Halaman publik blog (public.py) selalu override ini dengan tema
    # milik PEMILIK blog, jadi baris ini tidak berlaku di sana.
    if current_user.is_authenticated:
        return dict(page_theme=getattr(current_user, 'theme_preference', None) or 'light')
    return dict(page_theme='light')

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

from database import init_db, update_sitemap
with app.app_context():
    init_db()
    update_sitemap(app)

if __name__ == '__main__':
    app.run(debug=True)
