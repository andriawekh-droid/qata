import sqlite3
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE']
        )
        g.db.text_factory = lambda b: b.decode('utf-8', errors='replace')
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT,
            bio TEXT,
            website TEXT,
            twitter TEXT,
            instagram TEXT,
            threads TEXT,
            letterbird TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            can_upload_image INTEGER NOT NULL DEFAULT 0,
            is_premium INTEGER NOT NULL DEFAULT 0,
            premium_since TIMESTAMP,
            theme_preference TEXT NOT NULL DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invite_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by INTEGER NOT NULL,
            code TEXT UNIQUE NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            slug TEXT NOT NULL,
            content TEXT NOT NULL,
            content_html TEXT,
            reading_time INTEGER DEFAULT 1,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, slug)
        );

        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        );

        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            ip_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            UNIQUE(post_id, ip_hash)
        );

        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            slug TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_html TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, type),
            UNIQUE(user_id, slug)
        );

        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS register_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_register_attempts_ip
            ON register_attempts (ip_hash, created_at);

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            username TEXT,
            success INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_login_attempts_ip
            ON login_attempts (ip_hash, created_at);

        CREATE INDEX IF NOT EXISTS idx_login_attempts_user
            ON login_attempts (username, created_at);

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            note TEXT,
            proof_file TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_payments_user
            ON payments (user_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_payments_status
            ON payments (status, created_at);
    ''')
    db.commit()

    # Migrasi kolom tambahan pada users jika belum ada
    user_cols = [c['name'] for c in db.execute("PRAGMA table_info(users)").fetchall()]
    if 'can_upload_image' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN can_upload_image INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE users SET can_upload_image = 1 WHERE is_admin = 1")
        db.commit()
    if 'is_premium' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE users SET is_premium = 1 WHERE is_admin = 1")
        db.commit()
    if 'premium_since' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN premium_since TIMESTAMP")
        db.commit()
    if 'threads' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN threads TEXT")
        db.commit()
    if 'letterbird' not in user_cols:
        db.execute("ALTER TABLE users ADD COLUMN letterbird TEXT")
        db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)

def update_sitemap(app=None):
    from flask import current_app
    import os
    try:
        app_obj = app or current_app._get_current_object()
    except RuntimeError:
        return

    db = get_db()
    base_domain = os.environ.get('QATA_BASE_DOMAIN', 'qata.blog').strip().lower()
    subdomain_enabled = os.environ.get('QATA_SUBDOMAIN_ENABLED', '0').strip().lower() in ('1', 'true', 'yes', 'on')
    base_url = f'https://{base_domain}'

    def user_base(uname, is_prem):
        if subdomain_enabled and is_prem:
            return f'https://{uname}.{base_domain}'
        return f'{base_url}/{uname}'

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # Beranda utama & Jelajahi
    xml_lines.append(f'  <url><loc>{base_url}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
    xml_lines.append(f'  <url><loc>{base_url}/jelajahi</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>')

    # Blog & arsip pengguna aktif
    users = db.execute('SELECT username, is_premium, is_admin FROM users WHERE is_active = 1').fetchall()
    for u in users:
        uname = u['username']
        is_prem = bool(u['is_premium'] or u['is_admin'])
        ub = user_base(uname, is_prem)
        blog_root = f'{ub}/' if (subdomain_enabled and is_prem) else ub
        xml_lines.append(f'  <url><loc>{blog_root}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')
        xml_lines.append(f'  <url><loc>{ub}/tulisan</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>')
        xml_lines.append(f'  <url><loc>{ub}/tentang</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>')

    # Tulisan yang terbit
    posts = db.execute('''
        SELECT p.slug, p.updated_at, p.created_at, u.username, u.is_premium, u.is_admin
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.status = 'published' AND u.is_active = 1
        ORDER BY p.created_at DESC
    ''').fetchall()
    for p in posts:
        uname = p['username']
        is_prem = bool(p['is_premium'] or p['is_admin'])
        ub = user_base(uname, is_prem)
        slug = p['slug']
        tgl = str(p['updated_at'] or p['created_at'] or '')[:10]
        lastmod = f'<lastmod>{tgl}</lastmod>' if tgl else ''
        xml_lines.append(f'  <url><loc>{ub}/{slug}</loc>{lastmod}<changefreq>monthly</changefreq><priority>0.9</priority></url>')

    # Halaman custom
    pages = db.execute('''
        SELECT pg.slug, pg.updated_at, u.username, u.is_premium, u.is_admin
        FROM pages pg
        JOIN users u ON pg.user_id = u.id
        WHERE pg.type = 'custom' AND u.is_active = 1
    ''').fetchall()
    for pg in pages:
        uname = pg['username']
        is_prem = bool(pg['is_premium'] or pg['is_admin'])
        ub = user_base(uname, is_prem)
        slug = pg['slug']
        tgl = str(pg['updated_at'] or '')[:10]
        lastmod = f'<lastmod>{tgl}</lastmod>' if tgl else ''
        xml_lines.append(f'  <url><loc>{ub}/page/{slug}</loc>{lastmod}<changefreq>monthly</changefreq><priority>0.6</priority></url>')

    xml_lines.append('</urlset>\n')
    xml_content = '\n'.join(xml_lines)

    sitemap_path = os.path.join(app_obj.root_path, 'static', 'sitemap.xml')
    try:
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
    except Exception as e:
        app_obj.logger.warning(f"Gagal memperbarui sitemap.xml: {e}")
