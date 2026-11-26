import os
import secrets
import sqlite3
from urllib.parse import urlsplit
from flask import Flask, send_from_directory, g, request, url_for, redirect, flash
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from i18n import (
    SUPPORTED_LANGS,
    LANG_COOKIE,
    detect_lang,
    get_lang,
    t,
    format_date_localized,
    format_relative_time_localized,
    format_money,
)

BASE_DOMAIN = os.environ.get('QATA_BASE_DOMAIN', 'qata.blog').strip().lower()
SUBDOMAIN_ENABLED = os.environ.get('QATA_SUBDOMAIN_ENABLED', '0').strip().lower() in ('1', 'true', 'yes', 'on')

class SubdomainRouterMiddleware:
    """Memetakan permintaan <username>.<base_domain> ke rute /<username>/..."""

    PASSTHROUGH_PREFIXES = ('/static/', '/like/', '/.well-known/', '/lang/')
    PASSTHROUGH_PATHS = ('/favicon.ico', '/robots.txt')
    MAIN_DOMAIN_EXACT = (
        '/masuk', '/daftar', '/keluar',
        '/jelajahi', '/explore', '/discover',
        '/jelajahi/acak', '/discover/random',
    )

    def __init__(self, wsgi_app, base_domain):
        self.wsgi_app = wsgi_app
        self.base_domain = base_domain

    def _redirect(self, start_response, location, status='302 Found'):
        start_response(status, [
            ('Location', location),
            ('Content-Length', '0'),
            ('Cache-Control', 'no-store') if status.startswith('302') else ('Cache-Control', 'public, max-age=300'),
        ])
        return [b'']

    def __call__(self, environ, start_response):
        host = (environ.get('HTTP_HOST') or '').split(':')[0].strip().lower()
        suffix = '.' + self.base_domain
        if host.endswith(suffix) and len(host) > len(suffix):
            sub = host[:-len(suffix)]
            if sub and '.' not in sub:
                path = environ.get('PATH_INFO', '/') or '/'
                qs = environ.get('QUERY_STRING', '')
                qs_suffix = ('?' + qs) if qs else ''

                if sub == 'www':
                    return self._redirect(
                        start_response,
                        f'https://{self.base_domain}{path}{qs_suffix}',
                        status='301 Moved Permanently',
                    )

                if path in self.PASSTHROUGH_PATHS or path.startswith(self.PASSTHROUGH_PREFIXES):
                    return self.wsgi_app(environ, start_response)

                if path == '/dashboard' or path.startswith('/dashboard/') or path in self.MAIN_DOMAIN_EXACT:
                    return self._redirect(
                        start_response,
                        f'https://{self.base_domain}{path}{qs_suffix}',
                        status='302 Found',
                    )

                if path == f'/{sub}' or path.startswith(f'/{sub}/'):
                    stripped = path[len(sub) + 1:] or '/'
                    return self._redirect(
                        start_response,
                        f'https://{sub}.{self.base_domain}{stripped}{qs_suffix}',
                        status='301 Moved Permanently',
                    )

                environ['PATH_INFO'] = f'/{sub}' if path == '/' else f'/{sub}{path}'
                environ['HTTP_X_QATA_SUBDOMAIN_USER'] = sub

        return self.wsgi_app(environ, start_response)

app = Flask(__name__, instance_relative_config=True)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.wsgi_app = SubdomainRouterMiddleware(app.wsgi_app, BASE_DOMAIN)

_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    raise RuntimeError('Environment variable SECRET_KEY belum diset. Aplikasi tidak dijalankan.')

app.config.from_mapping(
    SECRET_KEY=_secret_key,
    DATABASE=app.instance_path + '/qata.db',
    BASE_DOMAIN=BASE_DOMAIN,
    SUBDOMAIN_ENABLED=SUBDOMAIN_ENABLED,
)

@app.before_request
def set_request_context():
    g.csp_nonce = secrets.token_urlsafe(16)
    g.subdomain_user = request.environ.get('HTTP_X_QATA_SUBDOMAIN_USER')
    g.lang = detect_lang(request)

@app.after_request
def set_security_headers(response):
    response.vary.add('Accept-Language')
    response.vary.add('Cookie')
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

@app.route('/lang/<lang_code>')
def set_language(lang_code):
    lang = lang_code.strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = 'id'

    raw_next = (request.args.get('next') or request.referrer or '/').strip()
    target = '/'
    if raw_next.startswith('/') and not raw_next.startswith('//'):
        target = raw_next
    elif raw_next:
        parsed = urlsplit(raw_next)
        host = (parsed.hostname or '').lower()
        if parsed.scheme in ('http', 'https') and (
            host == BASE_DOMAIN
            or host.endswith('.' + BASE_DOMAIN)
            or host in ('localhost', '127.0.0.1')
            or host.endswith('.localhost')
        ):
            target = raw_next

    resp = redirect(target)
    cookie_kwargs = dict(max_age=31536000, samesite='Lax', httponly=True)
    req_host = (request.host or '').split(':')[0].strip().lower()
    if '.' in BASE_DOMAIN and (req_host == BASE_DOMAIN or req_host.endswith('.' + BASE_DOMAIN)):
        cookie_kwargs['domain'] = '.' + BASE_DOMAIN
    resp.set_cookie(LANG_COOKIE, lang, **cookie_kwargs)
    return resp

@app.template_filter('tanggal')
def format_tanggal(value):
    return format_date_localized(value)

@app.template_filter('waktu_relatif')
def format_waktu_relatif(value):
    return format_relative_time_localized(value)

@app.template_filter('rupiah')
def format_rupiah(value):
    return format_money(value, 'IDR')

@app.template_filter('money')
def format_money_filter(value, currency='IDR'):
    return format_money(value, currency)

def switch_lang_url(lang_code):
    try:
        next_path = request.full_path.rstrip('?') or '/'
    except RuntimeError:
        next_path = '/'
    return url_for('set_language', lang_code=lang_code, next=next_path)

def main_url(endpoint, **values):
    """Bangun URL menuju domain utama (berguna saat user mengakses subdomain)."""
    rel = url_for(endpoint, **values)
    if getattr(g, 'subdomain_user', None) and rel.startswith('/'):
        return f"https://{BASE_DOMAIN}{rel}"
    return rel

def blog_url(user_or_username, subpath='', is_premium=None, external=False):
    """Bangun URL blog pengguna (otomatis memakai subdomain jika Premium & aktif)."""
    if isinstance(user_or_username, str):
        uname = user_or_username
        prem = bool(is_premium)
    else:
        uname = user_or_username['username'] if isinstance(user_or_username, (dict, sqlite3.Row)) else user_or_username.username
        if is_premium is not None:
            prem = bool(is_premium)
        elif isinstance(user_or_username, (dict, sqlite3.Row)):
            keys = user_or_username.keys()
            prem = bool((user_or_username['is_premium'] if 'is_premium' in keys else 0) or (user_or_username['is_admin'] if 'is_admin' in keys else 0))
        else:
            prem = bool(getattr(user_or_username, 'is_premium', False) or getattr(user_or_username, 'is_admin', False))

    if subpath and not subpath.startswith('/'):
        subpath = '/' + subpath

    sub_user = getattr(g, 'subdomain_user', None)
    if SUBDOMAIN_ENABLED and prem:
        if sub_user == uname and not external:
            return subpath or '/'
        return f"https://{uname}.{BASE_DOMAIN}{subpath or '/'}"

    if sub_user == uname:
        if external:
            return f"https://{uname}.{BASE_DOMAIN}{subpath or '/'}"
        return subpath or '/'

    rel = f"/{uname}{subpath}"
    if external:
        try:
            return f"{request.url_root.rstrip('/')}{rel}"
        except RuntimeError:
            return f"https://{BASE_DOMAIN}{rel}"
    return rel

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
    return dict(
        page_theme=theme,
        csp_nonce=nonce,
        main_url=main_url,
        blog_url=blog_url,
        base_domain=BASE_DOMAIN,
        subdomain_enabled=SUBDOMAIN_ENABLED,
        t=t,
        current_lang=get_lang(),
        switch_lang_url=switch_lang_url,
        format_money=format_money,
    )

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.unauthorized_handler
def unauthorized():
    flash(t('auth.login_required'), 'error')
    return redirect(url_for('auth.login'))

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
