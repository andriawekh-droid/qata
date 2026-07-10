import re
import hashlib
import mistune
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from database import get_db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

BATAS_UNDANGAN = 5
BATAS_PAGE = 3

def generate_slug(title):
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug

def render_markdown(content):
    markdown = mistune.create_markdown(
        plugins=['strikethrough', 'table']
    )
    return markdown(content)

def hitung_waktu_baca(content):
    jumlah_kata = len(content.split())
    menit = max(1, round(jumlah_kata / 200))
    return menit

@dashboard_bp.route('/')
@login_required
def index():
    db = get_db()
    posts = db.execute(
        '''SELECT p.*,
           COUNT(DISTINCT pv.id) as view_count,
           COUNT(DISTINCT l.id) as like_count
           FROM posts p
           LEFT JOIN page_views pv ON p.id = pv.post_id
           LEFT JOIN likes l ON p.id = l.post_id
           WHERE p.user_id = ?
           GROUP BY p.id
           ORDER BY p.created_at DESC''',
        (current_user.id,)
    ).fetchall()
    return render_template('dashboard/index.html', posts=posts)

@dashboard_bp.route('/tulisan/baru', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        status = request.form.get('status', 'draft')
        error = None

        if not title:
            error = 'Judul tidak boleh kosong.'
        elif not content:
            error = 'Isi tulisan tidak boleh kosong.'

        if error is None:
            db = get_db()
            slug = generate_slug(title)

            existing = db.execute(
                'SELECT id FROM posts WHERE user_id = ? AND slug = ?',
                (current_user.id, slug)
            ).fetchone()
            if existing:
                slug = slug + '-' + str(int(__import__('time').time()))

            content_html = render_markdown(content)
            reading_time = hitung_waktu_baca(content)
            db.execute(
                '''INSERT INTO posts (user_id, title, slug, content, content_html, reading_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (current_user.id, title, slug, content, content_html, reading_time, status)
            )
            db.commit()
            flash('Tulisan berhasil disimpan.', 'sukses')
            return redirect(url_for('dashboard.index'))

        flash(error, 'error')

    return render_template('dashboard/editor.html', post=None)

@dashboard_bp.route('/tulisan/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    db = get_db()
    post = db.execute(
        'SELECT * FROM posts WHERE id = ? AND user_id = ?',
        (post_id, current_user.id)
    ).fetchone()

    if post is None:
        flash('Tulisan tidak ditemukan.', 'error')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        status = request.form.get('status', 'draft')
        error = None

        if not title:
            error = 'Judul tidak boleh kosong.'
        elif not content:
            error = 'Isi tulisan tidak boleh kosong.'

        if error is None:
            content_html = render_markdown(content)
            reading_time = hitung_waktu_baca(content)
            db.execute(
                '''UPDATE posts
                   SET title = ?, content = ?, content_html = ?, reading_time = ?, status = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND user_id = ?''',
                (title, content, content_html, reading_time, status, post_id, current_user.id)
            )
            db.commit()
            flash('Tulisan berhasil diperbarui.', 'sukses')
            return redirect(url_for('dashboard.index'))

        flash(error, 'error')

    return render_template('dashboard/editor.html', post=post)

@dashboard_bp.route('/tulisan/hapus/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    db = get_db()
    post = db.execute(
        'SELECT * FROM posts WHERE id = ? AND user_id = ?',
        (post_id, current_user.id)
    ).fetchone()

    if post is None:
        flash('Tulisan tidak ditemukan.', 'error')
        return redirect(url_for('dashboard.index'))

    db.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM page_views WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    flash('Tulisan berhasil dihapus.', 'sukses')
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        display_name = request.form['display_name'].strip()
        website = request.form['website'].strip()
        twitter = request.form['twitter'].strip()
        instagram = request.form['instagram'].strip()
        error = None

        if not display_name:
            error = 'Nama tampilan tidak boleh kosong.'

        if error is None:
            db = get_db()
            db.execute(
                '''UPDATE users
                   SET display_name = ?, website = ?, twitter = ?, instagram = ?
                   WHERE id = ?''',
                (display_name, website, twitter, instagram, current_user.id)
            )
            db.commit()
            flash('Profil berhasil diperbarui.', 'sukses')
            return redirect(url_for('dashboard.profile'))

        flash(error, 'error')

    return render_template('dashboard/profil.html')

@dashboard_bp.route('/kode-undangan')
@login_required
def invite_codes():
    db = get_db()
    codes = db.execute(
        'SELECT * FROM invite_codes WHERE created_by = ? ORDER BY created_at DESC',
        (current_user.id,)
    ).fetchall()

    total_codes = len(codes)
    bisa_buat = current_user.is_admin or total_codes < BATAS_UNDANGAN

    return render_template('dashboard/undangan.html',
                           codes=codes,
                           total_codes=total_codes,
                           batas=BATAS_UNDANGAN,
                           bisa_buat=bisa_buat)

@dashboard_bp.route('/kode-undangan/buat', methods=['POST'])
@login_required
def create_invite_code():
    db = get_db()

    if not current_user.is_admin:
        total_codes = db.execute(
            'SELECT COUNT(*) FROM invite_codes WHERE created_by = ?',
            (current_user.id,)
        ).fetchone()[0]

        if total_codes >= BATAS_UNDANGAN:
            flash(f'Anda hanya dapat membuat maksimal {BATAS_UNDANGAN} kode undangan.', 'error')
            return redirect(url_for('dashboard.invite_codes'))

    import secrets
    code = secrets.token_urlsafe(8)
    db.execute(
        'INSERT INTO invite_codes (code, created_by) VALUES (?, ?)',
        (code, current_user.id)
    )
    db.commit()
    flash(f'Kode undangan berhasil dibuat: {code}', 'sukses')
    return redirect(url_for('dashboard.invite_codes'))

# Page routes
@dashboard_bp.route('/pages')
@login_required
def pages():
    db = get_db()
    user_pages = db.execute(
        'SELECT * FROM pages WHERE user_id = ? ORDER BY type',
        (current_user.id,)
    ).fetchall()

    total_custom = sum(1 for p in user_pages if p['type'] == 'custom')
    bisa_buat = total_custom < 1

    return render_template('dashboard/pages.html',
                           pages=user_pages,
                           bisa_buat=bisa_buat)

@dashboard_bp.route('/pages/edit/<int:page_id>', methods=['GET', 'POST'])
@login_required
def edit_page(page_id):
    db = get_db()
    page = db.execute(
        'SELECT * FROM pages WHERE id = ? AND user_id = ?',
        (page_id, current_user.id)
    ).fetchone()

    if page is None:
        flash('Halaman tidak ditemukan.', 'error')
        return redirect(url_for('dashboard.pages'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        error = None

        if not title:
            error = 'Judul tidak boleh kosong.'
        elif not content:
            error = 'Isi halaman tidak boleh kosong.'

        if error is None:
            content_html = render_markdown(content)
            db.execute(
                '''UPDATE pages
                   SET title = ?, content = ?, content_html = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND user_id = ?''',
                (title, content, content_html, page_id, current_user.id)
            )
            db.commit()
            flash('Halaman berhasil diperbarui.', 'sukses')
            return redirect(url_for('dashboard.pages'))

        flash(error, 'error')

    return render_template('dashboard/editor_page.html', page=page)

@dashboard_bp.route('/pages/baru', methods=['GET', 'POST'])
@login_required
def new_page():
    db = get_db()
    total_custom = db.execute(
        'SELECT COUNT(*) FROM pages WHERE user_id = ? AND type = "custom"',
        (current_user.id,)
    ).fetchone()[0]

    if total_custom >= 1:
        flash('Anda hanya dapat membuat 1 halaman bebas.', 'error')
        return redirect(url_for('dashboard.pages'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        error = None

        if not title:
            error = 'Judul tidak boleh kosong.'
        elif not content:
            error = 'Isi halaman tidak boleh kosong.'

        if error is None:
            slug = generate_slug(title)

            existing = db.execute(
                'SELECT id FROM pages WHERE user_id = ? AND slug = ?',
                (current_user.id, slug)
            ).fetchone()
            if existing:
                slug = slug + '-' + str(int(__import__('time').time()))

            content_html = render_markdown(content)
            db.execute(
                '''INSERT INTO pages (user_id, type, slug, title, content, content_html)
                   VALUES (?, 'custom', ?, ?, ?, ?)''',
                (current_user.id, slug, title, content, content_html)
            )
            db.commit()
            flash('Halaman berhasil dibuat.', 'sukses')
            return redirect(url_for('dashboard.pages'))

        flash(error, 'error')

    return render_template('dashboard/editor_page.html', page=None)

@dashboard_bp.route('/pages/hapus/<int:page_id>', methods=['POST'])
@login_required
def delete_page(page_id):
    db = get_db()
    page = db.execute(
        'SELECT * FROM pages WHERE id = ? AND user_id = ?',
        (page_id, current_user.id)
    ).fetchone()

    if page is None:
        flash('Halaman tidak ditemukan.', 'error')
        return redirect(url_for('dashboard.pages'))

    if page['type'] in ('landing', 'tentang'):
        flash('Halaman ini tidak dapat dihapus.', 'error')
        return redirect(url_for('dashboard.pages'))

    db.execute('DELETE FROM pages WHERE id = ?', (page_id,))
    db.commit()
    flash('Halaman berhasil dihapus.', 'sukses')
    return redirect(url_for('dashboard.pages'))

# Admin routes
@dashboard_bp.route('/admin')
@login_required
def admin_index():
    if not current_user.is_admin:
        abort(403)

    db = get_db()
    users = db.execute(
        '''SELECT u.*,
           COUNT(DISTINCT p.id) as post_count
           FROM users u
           LEFT JOIN posts p ON u.id = p.user_id
           GROUP BY u.id
           ORDER BY u.created_at DESC'''
    ).fetchall()

    return render_template('dashboard/admin.html', users=users)

@dashboard_bp.route('/admin/hapus-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(403)

    if user_id == current_user.id:
        flash('Anda tidak dapat menghapus akun sendiri.', 'error')
        return redirect(url_for('dashboard.admin_index'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user is None:
        flash('User tidak ditemukan.', 'error')
        return redirect(url_for('dashboard.admin_index'))

    post_ids = db.execute(
        'SELECT id FROM posts WHERE user_id = ?', (user_id,)
    ).fetchall()

    for post in post_ids:
        db.execute('DELETE FROM likes WHERE post_id = ?', (post['id'],))
        db.execute('DELETE FROM page_views WHERE post_id = ?', (post['id'],))

    db.execute('DELETE FROM posts WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM pages WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM invite_codes WHERE created_by = ?', (user_id,))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()

    flash(f'User @{user["username"]} dan semua datanya berhasil dihapus.', 'sukses')
    return redirect(url_for('dashboard.admin_index'))

@dashboard_bp.route('/admin/landing', methods=['GET', 'POST'])
@login_required
def admin_landing():
    if not current_user.is_admin:
        abort(403)

    db = get_db()

    if request.method == 'POST':
        settings = [
            ('landing_brand_sub', request.form['landing_brand_sub'].strip()),
            ('landing_title', request.form['landing_title'].strip()),
            ('landing_desc', request.form['landing_desc'].strip()),
            ('landing_features', request.form['landing_features'].strip()),
            ('landing_cta', request.form['landing_cta'].strip()),
        ]

        for key, value in settings:
            db.execute(
                '''INSERT INTO site_settings (key, value)
                   VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP''',
                (key, value, value)
            )
        db.commit()
        flash('Landing page berhasil diperbarui.', 'sukses')
        return redirect(url_for('dashboard.admin_landing'))

    settings = {}
    rows = db.execute('SELECT key, value FROM site_settings').fetchall()
    for row in rows:
        settings[row['key']] = row['value']

    return render_template('dashboard/admin_landing.html', settings=settings)

@dashboard_bp.route('/sistem')
@login_required
def sistem():
    if not current_user.is_admin:
        abort(403)

    import psutil
    from datetime import datetime

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    swap = psutil.swap_memory()

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_str = f"{uptime.days} hari, {uptime.seconds // 3600} jam, {(uptime.seconds % 3600) // 60} menit"

    db = get_db()
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_posts = db.execute('SELECT COUNT(*) FROM posts WHERE status = "published"').fetchone()[0]
    total_views = db.execute('SELECT COUNT(*) FROM page_views').fetchone()[0]
    total_likes = db.execute('SELECT COUNT(*) FROM likes').fetchone()[0]
    total_drafts = db.execute('SELECT COUNT(*) FROM posts WHERE status = "draft"').fetchone()[0]

    stats = {
        'cpu': cpu,
        'ram_used': round(ram.used / 1024 / 1024),
        'ram_total': round(ram.total / 1024 / 1024),
        'ram_percent': ram.percent,
        'disk_used': round(disk.used / 1024 / 1024 / 1024, 1),
        'disk_total': round(disk.total / 1024 / 1024 / 1024, 1),
        'disk_percent': disk.percent,
        'swap_used': round(swap.used / 1024 / 1024),
        'swap_total': round(swap.total / 1024 / 1024),
        'swap_percent': swap.percent,
        'uptime': uptime_str,
        'total_users': total_users,
        'total_posts': total_posts,
        'total_drafts': total_drafts,
        'total_views': total_views,
        'total_likes': total_likes,
    }

    return render_template('dashboard/sistem.html', stats=stats)