import hashlib
from flask import Blueprint, render_template, request, abort, jsonify
from database import get_db

public_bp = Blueprint('public', __name__)

def hash_ip(ip):
    return hashlib.sha256(ip.encode()).hexdigest()

def get_site_setting(db, key, default=''):
    row = db.execute(
        'SELECT value FROM site_settings WHERE key = ?', (key,)
    ).fetchone()
    return row['value'] if row else default

@public_bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        '''SELECT p.*, u.username, u.display_name,
           COUNT(DISTINCT l.id) as like_count
           FROM posts p
           JOIN users u ON p.user_id = u.id
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.status = 'published' AND u.is_active = 1
           GROUP BY p.id
           ORDER BY like_count DESC, p.created_at DESC
           LIMIT 20'''
    ).fetchall()

    settings = {
        'landing_title': get_site_setting(db, 'landing_title'),
        'landing_desc': get_site_setting(db, 'landing_desc'),
        'landing_features': get_site_setting(db, 'landing_features').split('\n'),
        'landing_cta': get_site_setting(db, 'landing_cta'),
        'landing_brand_sub': get_site_setting(db, 'landing_brand_sub'),
    }

    return render_template('public/index.html', posts=posts, settings=settings)

@public_bp.route('/<username>')
def user_blog(username):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    posts = db.execute(
        '''SELECT p.*, COUNT(DISTINCT l.id) as like_count
           FROM posts p
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.user_id = ? AND p.status = 'published'
           GROUP BY p.id
           ORDER BY p.created_at DESC''',
        (user['id'],)
    ).fetchall()

    # Ambil page landing user kalau ada
    landing_page = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'landing')
    ).fetchone()

    # Ambil page custom
    custom_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'custom')
    ).fetchall()

    return render_template('public/blog.html',
                           user=user,
                           posts=posts,
                           landing_page=landing_page,
                           custom_pages=custom_pages)

@public_bp.route('/<username>/tentang')
def user_about(username):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    # Ambil page tentang dari tabel pages
    page = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'tentang')
    ).fetchone()

    # Ambil page custom untuk navigasi
    custom_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'custom')
    ).fetchall()

    return render_template('public/tentang.html',
                           user=user,
                           page=page,
                           custom_pages=custom_pages)

@public_bp.route('/<username>/page/<slug>')
def user_page(username, slug):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    page = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND slug = ? AND type = ?',
        (user['id'], slug, 'custom')
    ).fetchone()

    if page is None:
        abort(404)

    # Ambil page custom lain untuk navigasi
    custom_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'custom')
    ).fetchall()

    return render_template('public/page.html',
                           user=user,
                           page=page,
                           custom_pages=custom_pages)

@public_bp.route('/<username>/<slug>')
def post_detail(username, slug):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    post = db.execute(
        '''SELECT p.*, COUNT(DISTINCT l.id) as like_count
           FROM posts p
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.user_id = ? AND p.slug = ? AND p.status = 'published'
           GROUP BY p.id''',
        (user['id'], slug)
    ).fetchone()

    if post is None:
        abort(404)

    # Catat kunjungan
    db.execute('INSERT INTO page_views (post_id) VALUES (?)', (post['id'],))
    db.commit()

    # Cek apakah IP ini sudah like
    ip_hash = hash_ip(request.remote_addr)
    sudah_like = db.execute(
        'SELECT id FROM likes WHERE post_id = ? AND ip_hash = ?',
        (post['id'], ip_hash)
    ).fetchone() is not None

    # Ambil page custom untuk navigasi
    custom_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'custom')
    ).fetchall()

    return render_template('public/post.html',
                           user=user,
                           post=post,
                           sudah_like=sudah_like,
                           custom_pages=custom_pages)

@public_bp.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    db = get_db()
    post = db.execute(
        'SELECT * FROM posts WHERE id = ? AND status = "published"',
        (post_id,)
    ).fetchone()

    if post is None:
        return jsonify({'error': 'Post tidak ditemukan'}), 404

    ip_hash = hash_ip(request.remote_addr)
    sudah_like = db.execute(
        'SELECT id FROM likes WHERE post_id = ? AND ip_hash = ?',
        (post_id, ip_hash)
    ).fetchone()

    if sudah_like:
        db.execute(
            'DELETE FROM likes WHERE post_id = ? AND ip_hash = ?',
            (post_id, ip_hash)
        )
        db.commit()
        liked = False
    else:
        db.execute(
            'INSERT INTO likes (post_id, ip_hash) VALUES (?, ?)',
            (post_id, ip_hash)
        )
        db.commit()
        liked = True

    total = db.execute(
        'SELECT COUNT(*) FROM likes WHERE post_id = ?',
        (post_id,)
    ).fetchone()[0]

    return jsonify({'liked': liked, 'total': total})

@public_bp.app_errorhandler(404)
def not_found(e):
    return render_template('public/404.html'), 404

@public_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('public/404.html'), 403