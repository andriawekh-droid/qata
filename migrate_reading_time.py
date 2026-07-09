import sqlite3

def migrate():
    conn = sqlite3.connect('instance/qata.db')
    conn.row_factory = sqlite3.Row

    # Tambah kolom reading_time kalau belum ada
    try:
        conn.execute('ALTER TABLE posts ADD COLUMN reading_time INTEGER DEFAULT 1')
        print("✓ Kolom reading_time ditambahkan.")
    except sqlite3.OperationalError as e:
        print(f"⚠ Kolom mungkin sudah ada: {e}")

    # Hitung ulang reading_time untuk semua post yang sudah ada
    posts = conn.execute('SELECT id, content FROM posts').fetchall()
    for post in posts:
        content = post['content'] or ''
        jumlah_kata = len(content.split())
        menit = max(1, round(jumlah_kata / 200))
        conn.execute(
            'UPDATE posts SET reading_time = ? WHERE id = ?',
            (menit, post['id'])
        )
        print(f"✓ Post ID {post['id']}: {menit} menit baca")

    conn.commit()
    conn.close()
    print("\nMigrasi reading_time selesai!")

if __name__ == '__main__':
    migrate()