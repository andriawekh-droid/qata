"""
Migration: tambah kolom theme_preference ke tabel users.
Jalankan sekali di VPS setelah git pull, sebelum restart service.

Cara pakai (di VPS, dari root folder project, venv aktif):
    python3 migrate_theme.py
"""
import sqlite3
import sys
import os

DB_PATH = os.environ.get('QATA_DB_PATH', 'instance/qata.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database tidak ditemukan di: {DB_PATH}")
        print("Set path yang benar via env var QATA_DB_PATH, atau jalankan dari root folder project.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]

    if 'theme_preference' in columns:
        print("Kolom theme_preference sudah ada. Tidak ada perubahan.")
        conn.close()
        return

    print("Menambahkan kolom theme_preference ke tabel users...")
    cur.execute(
        "ALTER TABLE users ADD COLUMN theme_preference TEXT NOT NULL DEFAULT 'light'"
    )
    conn.commit()

    # Verifikasi
    cur.execute("PRAGMA table_info(users)")
    columns_after = [row[1] for row in cur.fetchall()]
    if 'theme_preference' in columns_after:
        print("Migrasi berhasil. Kolom theme_preference sudah aktif dengan default 'light'.")
    else:
        print("Migrasi gagal, kolom tidak ditemukan setelah ALTER TABLE.")
        sys.exit(1)

    conn.close()

if __name__ == '__main__':
    migrate()
