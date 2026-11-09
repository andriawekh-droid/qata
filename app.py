import os
import secrets
import sqlite3
from flask import Flask, send_from_directory, g
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, instance_relative_config=True)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    raise RuntimeError('Environment variable SECRET_KEY belum diset. Aplikasi tidak dijalankan.')

app.config.from_mapping(
    SECRET_KEY=_secret_key,
    DATABASE=app.instance_path + '/qata.db',
)

@app.before_request
def set_csp_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)

@app.after_request
def set_security_headers(response):
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-XSS-Protection', '1; mode=block')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault(
        'Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    nonce = getattr(g, 'csp_nonce', None)
    if not nonce:
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce

    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https:; "
        f"style-src 'self' 'nonce-{nonce}' https:; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'"
    )
    return response

@app.route('/.well-known/security.txt')
def security_txt():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'well-known'),
        'security.txt', mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'sitemap.xml', mimetype='application/xml')

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
    theme = 'light'
    if current_user.is_authenticated:
        theme = getattr(current_user, 'theme_preference', None) or 'light'
    nonce = getattr(g, 'csp_nonce', None)
    if not nonce:
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce
    return dict(page_theme=theme, csp_nonce=nonce)

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
