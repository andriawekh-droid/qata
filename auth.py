import hashlib
import random
import re
import sqlite3
import time

import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, UserMixin
from database import get_db

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, id, username, email, display_name, bio, website, twitter, instagram, is_admin, active, theme_preference='light', can_upload_image=0):
        self.id = id
        self.username = username
        self.email = email
        self.display_name = display_name
        self.bio = bio
        self.website = website
        self.twitter = twitter
        self.instagram = instagram
        self.is_admin = is_admin
        self.active = active
        self.theme_preference = theme_preference or 'light'
        self.can_upload_image = bool(can_upload_image or is_admin)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return bool(self.active)

def get_user_by_id(user_id):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if row:
        can_upload = row['can_upload_image'] if 'can_upload_image' in row.keys() else 0
        return User(
            row['id'], row['username'], row['email'],
            row['display_name'], row['bio'], row['website'],
            row['twitter'], row['instagram'], row['is_admin'],
            row['is_active'], row['theme_preference'],
            can_upload
        )
    return None

def get_user_by_username(username):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if row:
        can_upload = row['can_upload_image'] if 'can_upload_image' in row.keys() else 0
        return User(
            row['id'], row['username'], row['email'],
            row['display_name'], row['bio'], row['website'],
            row['twitter'], row['instagram'], row['is_admin'],
            row['is_active'], row['theme_preference'],
            can_upload
        )
    return None

MODE_OPEN = 'open'
MODE_INVITE = 'invite_only'
MODE_CLOSED = 'closed'
MODE_VALID = (MODE_OPEN, MODE_INVITE, MODE_CLOSED)

USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Username yang bentrok dengan rute/berkas aplikasi atau menyesatkan.
USERNAME_RESERVED = {
    'daftar', 'masuk', 'keluar', 'dashboard', 'like', 'static', 'admin',
    'administrator', 'qata', 'api', 'www', 'root', 'support', 'help',
    'robots', 'sitemap', 'favicon', 'login', 'logout', 'register',
    'tulisan', 'tentang', 'page', 'rss', 'sistem', 'system',
}

PASSWORD_MIN = 8
PASSWORD_MAX_BYTES = 72  # batas bcrypt

LIMIT_SUKSES_PER_JAM = 3
LIMIT_PERCOBAAN_PER_JAM = 15
MIN_DETIK_ISI_FORM = 2

# Rate limiting login (mencegah brute-force password)
MAX_LOGIN_GAGAL_USER = 5     # per 15 menit per username
MAX_LOGIN_GAGAL_IP = 20      # per 15 menit per IP

def get_registration_mode(db):
    """Mode pendaftaran dari site_settings. Default invite_only (aman)."""
    row = db.execute(
        "SELECT value FROM site_settings WHERE key = 'registration_mode'"
    ).fetchone()
    mode = row['value'] if row else MODE_INVITE
    return mode if mode in MODE_VALID else MODE_INVITE

def _ip_hash():
    return hashlib.sha256((request.remote_addr or '').encode()).hexdigest()

def _terlalu_banyak_percobaan(db, ip_hash):
    db.execute(
        "DELETE FROM register_attempts WHERE created_at < datetime('now', '-1 day')"
    )
    row = db.execute(
        '''SELECT COUNT(*) AS total, COALESCE(SUM(success), 0) AS ok
           FROM register_attempts
           WHERE ip_hash = ? AND created_at >= datetime('now', '-1 hour')''',
        (ip_hash,)
    ).fetchone()
    return row['ok'] >= LIMIT_SUKSES_PER_JAM or row['total'] >= LIMIT_PERCOBAAN_PER_JAM

def _terlalu_banyak_gagal_login(db, ip_hash, username):
    db.execute(
        "DELETE FROM login_attempts WHERE created_at < datetime('now', '-1 day')"
    )
    # Cek batas gagal per IP dalam 15 menit terakhir
    ip_fails = db.execute(
        '''SELECT COUNT(*) FROM login_attempts
           WHERE ip_hash = ? AND success = 0 AND created_at >= datetime('now', '-15 minutes')''',
        (ip_hash,)
    ).fetchone()[0]

    if ip_fails >= MAX_LOGIN_GAGAL_IP:
        return True

    # Cek batas gagal per username dalam 15 menit terakhir
    if username:
        user_fails = db.execute(
            '''SELECT COUNT(*) FROM login_attempts
               WHERE username = ? AND success = 0 AND created_at >= datetime('now', '-15 minutes')''',
            (username,)
        ).fetchone()[0]
        if user_fails >= MAX_LOGIN_GAGAL_USER:
            return True

    return False

def _buat_tantangan():
    a, b = random.randint(2, 9), random.randint(2, 9)
    session['reg_answer'] = str(a + b)
    session['reg_ts'] = time.time()
    return f'{a} + {b}'

def _render_register(mode, form=None, tantangan=None):
    form = form or {}
    if mode == MODE_OPEN and tantangan is None:
        tantangan = _buat_tantangan()
    return render_template(
        'auth/daftar.html',
        mode=mode,
        tantangan=tantangan,
        username=form.get('username', ''),
        email=form.get('email', ''),
    )

@auth_bp.route('/daftar', methods=['GET', 'POST'])
def register():
    db = get_db()
    mode = get_registration_mode(db)

    if mode == MODE_CLOSED:
        return render_template('auth/daftar.html', mode=mode)

    if request.method == 'GET':
        return _render_register(mode)

    # Honeypot: manusia tidak melihat kolom ini, bot biasanya mengisinya.
    # Pura-pura sukses agar bot tidak tahu ia ditolak.
    if request.form.get('website_url', '').strip():
        flash('Pendaftaran berhasil! Silakan login.', 'sukses')
        return redirect(url_for('auth.login'))

    ip_hash = _ip_hash()
    if _terlalu_banyak_percobaan(db, ip_hash):
        db.commit()
        flash('Terlalu banyak percobaan pendaftaran dari jaringan Anda. Coba lagi dalam satu jam.', 'error')
        return _render_register(mode, request.form)

    cur = db.execute(
        'INSERT INTO register_attempts (ip_hash, success) VALUES (?, 0)', (ip_hash,)
    )
    attempt_id = cur.lastrowid
    db.commit()

    username = request.form.get('username', '').strip().lower()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    invite_code = request.form.get('invite_code', '').strip()
    error = None

    expected = session.pop('reg_answer', None)
    rendered_at = session.pop('reg_ts', None)

    if mode == MODE_OPEN:
        jawaban = request.form.get('jawaban', '').strip()
        if expected is None or jawaban != expected:
            error = 'Jawaban pertanyaan keamanan salah.'
        elif rendered_at is None or time.time() - rendered_at < MIN_DETIK_ISI_FORM:
            error = 'Formulir dikirim terlalu cepat. Silakan coba lagi.'

    code_row = None
    if error is None and mode == MODE_INVITE:
        code_row = db.execute(
            'SELECT * FROM invite_codes WHERE code = ? AND used = 0',
            (invite_code,)
        ).fetchone()
        if not code_row:
            error = 'Kode undangan tidak valid atau sudah digunakan.'

    if error is None:
        if not username or not email or not password:
            error = 'Semua kolom wajib diisi.'
        elif not USERNAME_RE.match(username):
            error = 'Username 3-30 karakter: huruf kecil, angka, dan tanda hubung (tidak di awal/akhir).'
        elif username in USERNAME_RESERVED:
            error = 'Username ini tidak tersedia.'
        elif not EMAIL_RE.match(email):
            error = 'Format email tidak valid.'
        elif len(password) < PASSWORD_MIN:
            error = f'Password minimal {PASSWORD_MIN} karakter.'
        elif len(password.encode('utf-8')) > PASSWORD_MAX_BYTES:
            error = 'Password terlalu panjang (maksimal 72 byte).'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            error = 'Username sudah digunakan.'
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            error = 'Email sudah terdaftar.'

    if error is None:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Cek apakah ini user pertama — kalau iya, jadikan admin
        user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        is_admin = 1 if user_count == 0 else 0

        try:
            db.execute(
                '''INSERT INTO users
                   (username, email, password, display_name, is_admin)
                   VALUES (?, ?, ?, ?, ?)''',
                (username, email, hashed.decode('utf-8'), username, is_admin)
            )
            if code_row:
                db.execute(
                    'UPDATE invite_codes SET used = 1 WHERE code = ?',
                    (invite_code,)
                )
            db.execute(
                'UPDATE register_attempts SET success = 1 WHERE id = ?',
                (attempt_id,)
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            error = 'Username atau email sudah digunakan.'
        else:
            flash('Pendaftaran berhasil! Silakan login.', 'sukses')
            return redirect(url_for('auth.login'))

    flash(error, 'error')
    return _render_register(mode, request.form)

@auth_bp.route('/masuk', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        ip_hash = _ip_hash()

        # Cek rate limit login
        if _terlalu_banyak_gagal_login(db, ip_hash, username):
            db.commit()
            flash('Terlalu banyak percobaan login yang gagal. Silakan tunggu 15 menit sebelum mencoba lagi.', 'error')
            return render_template('auth/masuk.html', mode=get_registration_mode(db), username=username)

        row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        error = None

        if row is None:
            error = 'Username atau password salah.'
        elif not row['is_active']:
            error = 'Akun ini telah dinonaktifkan.'
        elif not bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
            error = 'Username atau password salah.'

        if error is None:
            # Catat login sukses
            db.execute(
                'INSERT INTO login_attempts (ip_hash, username, success) VALUES (?, ?, 1)',
                (ip_hash, username)
            )
            db.commit()

            user = User(
                row['id'], row['username'], row['email'],
                row['display_name'], row['bio'], row['website'],
                row['twitter'], row['instagram'], row['is_admin'],
                row['is_active'], row['theme_preference']
            )
            login_user(user)
            return redirect(url_for('dashboard.index'))

        # Catat login gagal
        db.execute(
            'INSERT INTO login_attempts (ip_hash, username, success) VALUES (?, ?, 0)',
            (ip_hash, username)
        )
        db.commit()

        flash(error, 'error')
        return render_template('auth/masuk.html', mode=get_registration_mode(db), username=username)

    return render_template('auth/masuk.html', mode=get_registration_mode(get_db()), username='')

@auth_bp.route('/keluar')
@login_required
def logout():
    logout_user()
    flash('Anda telah keluar.', 'sukses')
    return redirect(url_for('auth.login'))