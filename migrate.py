import sqlite3
import mistune

def render_markdown(content):
    markdown = mistune.create_markdown(plugins=['strikethrough', 'table'])
    return markdown(content)

def migrate():
    conn = sqlite3.connect('instance/qata.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Buat tabel baru kalau belum ada
    conn.executescript('''
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
    ''')

    # Auto-populate page Tentang dari bio yang sudah ada
    users = conn.execute('SELECT * FROM users').fetchall()
    for user in users:
        bio = user['bio'] or ''
        display_name = user['display_name'] or user['username']
        website = user['website'] or ''
        twitter = user['twitter'] or ''
        instagram = user['instagram'] or ''

        # Buat konten page Tentang
        tentang_content = f"# Tentang {display_name}\n\n"
        if bio:
            tentang_content += f"{bio}\n\n"

        links = []
        if website:
            links.append(f"- [Website]({website})")
        if twitter:
            links.append(f"- [Twitter/X](https://twitter.com/{twitter})")
        if instagram:
            links.append(f"- [Instagram](https://instagram.com/{instagram})")

        if links:
            tentang_content += "## Tautan\n\n" + "\n".join(links)

        tentang_html = render_markdown(tentang_content)

        # Insert page Tentang
        try:
            conn.execute(
                '''INSERT INTO pages (user_id, type, title, content, content_html)
                   VALUES (?, 'tentang', 'Tentang', ?, ?)''',
                (user['id'], tentang_content, tentang_html)
            )
            print(f"✓ Page Tentang dibuat untuk @{user['username']}")
        except sqlite3.IntegrityError:
            print(f"⚠ Page Tentang sudah ada untuk @{user['username']}, dilewati.")

        # Buat konten page Landing
        landing_content = f"# Halo, saya {display_name}\n\nSelamat datang di blog saya."
        landing_html = render_markdown(landing_content)

        try:
            conn.execute(
                '''INSERT INTO pages (user_id, type, title, content, content_html)
                   VALUES (?, 'landing', 'Halaman Utama', ?, ?)''',
                (user['id'], landing_content, landing_html)
            )
            print(f"✓ Page Landing dibuat untuk @{user['username']}")
        except sqlite3.IntegrityError:
            print(f"⚠ Page Landing sudah ada untuk @{user['username']}, dilewati.")

    # Populate site_settings untuk landing page Qata
    default_settings = [
        ('landing_title', 'Tempat tenang untuk menulis dan dibaca.'),
        ('landing_desc', 'Tanpa pelacak. Tanpa iklan. Tanpa tema yang membingungkan. Hanya halaman kosong, kursor, dan pembaca di seberang sana.'),
        ('landing_features', 'Tampil rapi di perangkat apa pun\nHalaman ringan, cepat dimuat\nTanpa pelacak, iklan, atau skrip\nDaftar dalam hitungan detik\nTulis dengan Markdown sederhana\nDibuat agar tetap awet'),
        ('landing_cta', 'Mulai menulis →'),
        ('landing_brand_sub', 'Platform blog yang sederhana, ringan, dan mengutamakan tulisan.'),
    ]

    for key, value in default_settings:
        try:
            conn.execute(
                'INSERT INTO site_settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            print(f"✓ Setting '{key}' dibuat.")
        except sqlite3.IntegrityError:
            print(f"⚠ Setting '{key}' sudah ada, dilewati.")

    conn.commit()
    conn.close()
    print("\nMigrasi selesai!")

if __name__ == '__main__':
    migrate()