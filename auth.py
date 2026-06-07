import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, UserMixin
from database import get_db

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, id, username, email, display_name, bio, website, twitter, instagram, is_admin, active):
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

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return bool(self.active)

def get_user_by_id(user_id):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if row:
        return User(
            row['id'], row['username'], row['email'],
            row['display_name'], row['bio'], row['website'],
            row['twitter'], row['instagram'], row['is_admin'],
            row['is_active']
        )
    return None

def get_user_by_username(username):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if row:
        return User(
            row['id'], row['username'], row['email'],
            row['display_name'], row['bio'], row['website'],
            row['twitter'], row['instagram'], row['is_admin'],
            row['is_active']
        )
    return None

@auth_bp.route('/daftar', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        invite_code = request.form['invite_code'].strip()

        db = get_db()
        error = None

        # Validasi kode undangan
        code_row = db.execute(
            'SELECT * FROM invite_codes WHERE code = ? AND used = 0',
            (invite_code,)
        ).fetchone()

        if not code_row:
            error = 'Kode undangan tidak valid atau sudah digunakan.'
        elif not username or not email or not password:
            error = 'Semua kolom wajib diisi.'
        elif len(username) < 3:
            error = 'Username minimal 3 karakter.'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            error = 'Username sudah digunakan.'
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            error = 'Email sudah terdaftar.'

        if error is None:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Cek apakah ini user pertama — kalau iya, jadikan admin
            user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            is_admin = 1 if user_count == 0 else 0

            db.execute(
                '''INSERT INTO users 
                   (username, email, password, display_name, is_admin)
                   VALUES (?, ?, ?, ?, ?)''',
                (username, email, hashed.decode('utf-8'), username, is_admin)
            )
            db.execute(
                'UPDATE invite_codes SET used = 1 WHERE code = ?',
                (invite_code,)
            )
            db.commit()
            flash('Pendaftaran berhasil! Silakan login.', 'sukses')
            return redirect(url_for('auth.login'))

        flash(error, 'error')

    return render_template('auth/daftar.html')

@auth_bp.route('/masuk', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']

        db = get_db()
        row = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        error = None

        if row is None:
            error = 'Username atau password salah.'
        elif not row['is_active']:
            error = 'Akun ini telah dinonaktifkan.'
        elif not bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
            error = 'Username atau password salah.'

        if error is None:
            user = User(
                row['id'], row['username'], row['email'],
                row['display_name'], row['bio'], row['website'],
                row['twitter'], row['instagram'], row['is_admin'],
                row['is_active']
            )
            login_user(user)
            return redirect(url_for('dashboard.index'))

        flash(error, 'error')

    return render_template('auth/masuk.html')

@auth_bp.route('/keluar')
@login_required
def logout():
    logout_user()
    flash('Anda telah keluar.', 'sukses')
    return redirect(url_for('auth.login'))