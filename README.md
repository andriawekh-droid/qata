# Qata

Platform blogging minimalis yang fokus pada tulisan. Dibangun dengan Python dan Flask.

**[qata.my.id](https://qata.my.id)**

---

## Filosofi

Qata dirancang dengan satu prinsip utama: tulisan adalah yang utama. Tidak ada iklan, tidak ada pelacak eksternal, tidak ada elemen visual yang mengganggu. Hanya penulis, teks, dan pembaca.

## Fitur

- Registrasi dengan kode undangan
- Editor Markdown
- Halaman blog per pengguna (`qata.my.id/username`)
- Halaman arsip tulisan per tahun
- Tulisan terbaru dan populer di beranda
- Sistem like/vote tanpa perlu login
- Halaman Pages (Utama, Tentang, dan satu halaman bebas)
- RSS Feed per pengguna
- Statistik kunjungan tanpa pelacak eksternal
- Panel admin
- Monitor status sistem (CPU, RAM, Disk)
- Landing page yang bisa diedit admin

## Tech Stack

- **Backend:** Python + Flask
- **Database:** SQLite (WAL mode)
- **Template:** Jinja2
- **Markdown:** Mistune
- **Auth:** Flask-Login + bcrypt
- **Server:** Gunicorn + Nginx
- **DNS/SSL:** Cloudflare

## Kenapa Ringan dan Aman

- Tidak ada JavaScript framework — halaman dirender di server (SSR)
- CSS murni tanpa library eksternal
- Font sistem, tidak ada request ke Google Fonts
- Markdown dirender saat disimpan, bukan saat dibaca
- Statistik kunjungan disimpan lokal, IP di-hash dengan SHA-256
- Tidak ada pelacak atau skrip pihak ketiga

## Instalasi Lokal

```bash
# Clone repository
git clone https://github.com/andriawekh-droid/qata.git
cd qata

# Buat virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install flask flask-login bcrypt mistune gunicorn psutil

# Jalankan
python app.py
```

Buka `http://127.0.0.1:5000` di browser.

## Deployment

Qata berjalan di VPS Ubuntu 22.04 dengan Gunicorn sebagai WSGI server dan Nginx sebagai reverse proxy. Wildcard SSL ditangani oleh Cloudflare.

Spesifikasi minimum: 1 CPU, 1GB RAM.

## Lisensi

MIT License — bebas digunakan dan dimodifikasi.

---

Dibuat oleh [awekh](https://qata.my.id/awekh)
