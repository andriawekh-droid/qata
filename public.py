import hashlib
import re
import mistune
from flask import Blueprint, render_template, request, abort, jsonify, Response, redirect, url_for, flash
from database import get_db

def render_markdown(content):
    markdown = mistune.create_markdown(plugins=['strikethrough', 'table'])
    return markdown(content)

def extract_excerpt(text, max_len=140):
    if not text:
        return ''
    # Hapus blok kode, inline code, dan gambar markdown
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Ganti tautan markdown dengan teks jangkar
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Hapus penanda judul, blockquote, bullet list
    text = re.sub(r'^[#>\-*\d+\.]+\s+', '', text, flags=re.MULTILINE)
    # Hapus karakter pemformatan
    text = re.sub(r'[*_~=]', '', text)
    # Hapus tag HTML jika ada
    text = re.sub(r'<[^>]+>', '', text)
    # Rapikan spasi
    text = ' '.join(text.split())
    if len(text) > max_len:
        return text[:max_len].rsplit(' ', 1)[0] + '...'
    return text

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

    # 3 tulisan terbaru dari semua user
    recent_posts = db.execute(
        '''SELECT p.*, u.username, u.display_name,
           COUNT(DISTINCT l.id) as like_count
           FROM posts p
           JOIN users u ON p.user_id = u.id
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.status = 'published' AND u.is_active = 1
           GROUP BY p.id
           ORDER BY p.created_at DESC
           LIMIT 3'''
    ).fetchall()

    # 3 tulisan populer dari semua user
    popular_posts = db.execute(
        '''SELECT p.*, u.username, u.display_name,
           COUNT(DISTINCT l.id) as like_count
           FROM posts p
           JOIN users u ON p.user_id = u.id
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.status = 'published' AND u.is_active = 1
           GROUP BY p.id
           ORDER BY like_count DESC, p.created_at DESC
           LIMIT 3'''
    ).fetchall()

    settings = {
        'landing_title': get_site_setting(db, 'landing_title'),
        'landing_desc': render_markdown(get_site_setting(db, 'landing_desc')),
        'landing_features': render_markdown(get_site_setting(db, 'landing_features')),
        'landing_cta': get_site_setting(db, 'landing_cta'),
        'landing_brand_sub': get_site_setting(db, 'landing_brand_sub'),
    }

    return render_template('public/index.html',
                           recent_posts=recent_posts,
                           popular_posts=popular_posts,
                           settings=settings)

@public_bp.route('/jelajahi')
@public_bp.route('/discover')
@public_bp.route('/explore')
def explore():
    db = get_db()
    current_filter = request.args.get('filter', 'acak').lower()
    if current_filter not in ('acak', 'terbaru', 'populer'):
        current_filter = 'acak'

    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = 15

    base_from = '''
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN likes l ON p.id = l.post_id
        WHERE p.status = 'published' AND u.is_active = 1
        GROUP BY p.id
    '''

    total_pages = 1
    if current_filter == 'acak':
        # Postingan acak dari para penulis di Qata
        posts = db.execute(
            f'''SELECT p.*, u.username, u.display_name,
                      COUNT(DISTINCT l.id) as like_count
               {base_from}
               ORDER BY RANDOM()
               LIMIT 20'''
        ).fetchall()
    elif current_filter == 'terbaru':
        count_row = db.execute(
            f'''SELECT COUNT(*) as total FROM (
                SELECT p.id {base_from}
            )'''
        ).fetchone()
        total_items = count_row['total'] if count_row else 0
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        posts = db.execute(
            f'''SELECT p.*, u.username, u.display_name,
                      COUNT(DISTINCT l.id) as like_count
               {base_from}
               ORDER BY p.created_at DESC
               LIMIT ? OFFSET ?''',
            (per_page, offset)
        ).fetchall()
    else:  # populer
        count_row = db.execute(
            f'''SELECT COUNT(*) as total FROM (
                SELECT p.id {base_from}
            )'''
        ).fetchone()
        total_items = count_row['total'] if count_row else 0
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        posts = db.execute(
            f'''SELECT p.*, u.username, u.display_name,
                      COUNT(DISTINCT l.id) as like_count
               {base_from}
               ORDER BY like_count DESC, p.created_at DESC
               LIMIT ? OFFSET ?''',
            (per_page, offset)
        ).fetchall()

    posts_data = []
    for p in posts:
        item = dict(p)
        item['excerpt'] = extract_excerpt(p['content'] if 'content' in p.keys() else '')
        posts_data.append(item)

    return render_template(
        'public/explore.html',
        posts=posts_data,
        current_filter=current_filter,
        page=page,
        total_pages=total_pages
    )

@public_bp.route('/jelajahi/acak')
@public_bp.route('/discover/random')
def random_post():
    db = get_db()
    row = db.execute(
        '''SELECT p.slug, u.username
           FROM posts p
           JOIN users u ON p.user_id = u.id
           WHERE p.status = 'published' AND u.is_active = 1
           ORDER BY RANDOM()
           LIMIT 1'''
    ).fetchone()

    if row:
        return redirect(url_for('public.post_detail', username=row['username'], slug=row['slug']))
    flash('Belum ada tulisan yang diterbitkan.', 'info')
    return redirect(url_for('public.explore'))

@public_bp.route('/<username>')
def user_blog(username):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    # 3 tulisan terbaru
    recent_posts = db.execute(
        '''SELECT p.*, COUNT(DISTINCT l.id) as like_count
           FROM posts p
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.user_id = ? AND p.status = 'published'
           GROUP BY p.id
           ORDER BY p.created_at DESC
           LIMIT 3''',
        (user['id'],)
    ).fetchall()

    # 3 tulisan populer
    popular_posts = db.execute(
        '''SELECT p.*, COUNT(DISTINCT l.id) as like_count
           FROM posts p
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.user_id = ? AND p.status = 'published'
           GROUP BY p.id
           ORDER BY like_count DESC, p.created_at DESC
           LIMIT 3''',
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
                           recent_posts=recent_posts,
                           popular_posts=popular_posts,
                           landing_page=landing_page,
                           custom_pages=custom_pages,
                           page_theme=user['theme_preference'] or 'light')

@public_bp.route('/<username>/tulisan')
def user_archive(username):
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

    # Kelompokkan per tahun
    archive = {}
    for post in posts:
        year = str(post['created_at'])[:4]
        if year not in archive:
            archive[year] = []
        archive[year].append(post)

    # Urutkan tahun terbaru di atas
    archive = dict(sorted(archive.items(), reverse=True))

    custom_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? AND type = ?',
        (user['id'], 'custom')
    ).fetchall()

    return render_template('public/archive.html',
                           user=user,
                           archive=archive,
                           custom_pages=custom_pages,
                           page_theme=user['theme_preference'] or 'light')

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
                           custom_pages=custom_pages,
                           page_theme=user['theme_preference'] or 'light')

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
                           custom_pages=custom_pages,
                           page_theme=user['theme_preference'] or 'light')

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
                           custom_pages=custom_pages,
                           page_theme=user['theme_preference'] or 'light')

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

@public_bp.route('/<username>/rss')
def user_rss(username):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        (username,)
    ).fetchone()

    if user is None:
        abort(404)

    posts = db.execute(
        '''SELECT * FROM posts
           WHERE user_id = ? AND status = 'published'
           ORDER BY created_at DESC
           LIMIT 20''',
        (user['id'],)
    ).fetchall()

    base_url = 'https://qata.my.id'
    blog_url = f"{base_url}/{username}"

    items = ''
    for post in posts:
        post_url = f"{base_url}/{username}/{post['slug']}"
        title = str(post['title']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        desc = str(post['content_html'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        pub_date = str(post['created_at'])[:19]

        items += f'''
        <item>
            <title>{title}</title>
            <link>{post_url}</link>
            <guid>{post_url}</guid>
            <description>{desc}</description>
            <pubDate>{pub_date}</pubDate>
        </item>'''

    display_name = str(user['display_name'] or username)
    bio = str(user['bio'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>{display_name}</title>
        <link>{blog_url}</link>
        <description>{bio}</description>
        <language>id</language>
        {items}
    </channel>
</rss>'''

    return Response(rss, mimetype='application/rss+xml')

@public_bp.app_errorhandler(404)
def not_found(e):
    return render_template('public/404.html'), 404

@public_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('public/404.html'), 403