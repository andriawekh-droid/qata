# Dokumentasi Teknis — Platform Qata

> Versi: 1.0 | Terakhir diperbarui: Juni 2026

---

## 1. Gambaran Umum

**Qata** (qata.my.id) adalah platform blogging minimalis berbasis teks yang dirancang dengan prinsip:

- **Privasi pengguna** — tidak ada pelacak eksternal (no third-party trackers)
- **Kecepatan muat** — ringan, tidak bergantung pada framework frontend berat
- **Server-side rendering (SSR)** — halaman dirender di sisi server, bukan browser
- **Monolitik** — tidak ada pemisahan frontend/backend via API; semua dalam satu aplikasi
- **Invite-only** — registrasi hanya bisa dilakukan dengan kode undangan

---

## 2. Stack Teknologi

| Komponen | Teknologi |
|---|---|
| Bahasa pemrograman | Python |
| Web framework | Flask |
| Template engine | Jinja2 |
| Parser Markdown | Mistune |
| Autentikasi | flask-login + bcrypt |
| Database | SQLite (mode WAL) |
| Application server | Gunicorn |
| Web server / reverse proxy | Nginx |
| Sistem operasi (VPS) | Ubuntu 22.04 LTS |
| DNS & SSL | Cloudflare |
| Version control | Git / GitHub (repo privat) |
| Monitoring sistem | psutil |

---

## 3. Arsitektur Sistem

```
Internet
   │
   ▼
Cloudflare (DNS + SSL Termination)
   │
   ▼
Nginx (Reverse Proxy, port 80/443)
   │
   ▼
Gunicorn (WSGI Application Server)
   │
   ▼
Flask Application (qata.my.id)
   │
   ▼
SQLite Database (WAL mode)
```

Semua komponen berjalan dalam satu VPS (DomainEsia, Ubuntu 22.04 LTS). Cloudflare menangani SSL/TLS sehingga koneksi antara pengguna dan Cloudflare selalu terenkripsi (HTTPS).

---

## 4. Struktur Database

Database menggunakan SQLite dengan mode WAL (Write-Ahead Logging) untuk performa dan keandalan yang lebih baik. Tabel-tabel utama:

### `users`
Menyimpan data pengguna terdaftar.

| Kolom | Keterangan |
|---|---|
| id | Primary key |
| username | Nama pengguna (unik) |
| password_hash | Hash password (bcrypt) |
| is_admin | Status admin (boolean) |
| created_at | Tanggal registrasi |

### `posts`
Menyimpan seluruh postingan blog.

| Kolom | Keterangan |
|---|---|
| id | Primary key |
| user_id | Foreign key ke `users` |
| title | Judul postingan |
| slug | URL-friendly identifier |
| content | Konten Markdown |
| view_count | Jumlah tampilan |
| like_count | Jumlah suka |
| created_at | Tanggal publikasi |

### `invite_codes`
Menyimpan kode undangan untuk registrasi.

| Kolom | Keterangan |
|---|---|
| id | Primary key |
| code | Kode unik (single-use) |
| used | Status pemakaian (boolean) |
| used_by | Username yang menggunakan |

### `pages`
Menyimpan halaman statis per pengguna.

| Kolom | Keterangan |
|---|---|
| id | Primary key |
| user_id | Foreign key ke `users` |
| page_type | Tipe halaman (landing, about, custom) |
| content | Konten Markdown |

### `site_settings`
Menyimpan konfigurasi halaman landing utama situs (dapat diedit admin).

---

## 5. Fitur Platform

### 5.1 Sistem Registrasi (Invite-only)
- Pengguna baru hanya bisa mendaftar menggunakan **kode undangan** satu kali pakai
- Kode dikelola oleh admin melalui panel admin

### 5.2 Autentikasi
- Login menggunakan `flask-login`
- Password disimpan dalam bentuk hash menggunakan `bcrypt`

### 5.3 Blog & Postingan
- Penulisan konten menggunakan **Markdown** (diproses oleh Mistune)
- URL postingan: `qata.my.id/{username}/{slug}`
- Setiap postingan memiliki statistik: jumlah tampilan dan jumlah suka

### 5.4 Dashboard Pengguna
- Manajemen postingan (buat, edit, hapus)
- Statistik tampilan dan suka per postingan

### 5.5 Halaman Statis (Pages)
Setiap pengguna memiliki hingga 3 halaman statis:
- **Landing** — halaman utama profil pengguna
- **About** — halaman tentang penulis
- **Custom** — satu halaman bebas tambahan

### 5.6 Panel Admin
- Dapat diakses oleh pengguna pertama yang terdaftar
- Fitur: kelola pengguna, hapus data, kelola kode undangan

### 5.7 RSS Feed
- Setiap pengguna memiliki feed RSS yang dapat dideteksi otomatis oleh browser
- URL feed: `qata.my.id/{username}/rss`

### 5.8 Halaman Arsip
- Postingan dikelompokkan berdasarkan tahun

### 5.9 Homepage & Blog Pengguna
Menampilkan dua seksi utama:
- **Terbaru** — 5 postingan terbaru
- **Populer** — 5 postingan dengan like terbanyak

### 5.10 Monitor Status Sistem
- Memantau kondisi server (CPU, memori, disk) menggunakan `psutil`

---

## 6. Deployment & Operasional

### 6.1 Proses Deployment
```bash
# Di VPS, tarik perubahan terbaru dari GitHub
git pull

# Restart layanan aplikasi
systemctl restart qata
```

### 6.2 Backup Database
Backup otomatis berjalan setiap hari pukul 02:00 via cron job.

### 6.3 Version Control
- Repository: GitHub (publik, `andriawekh-droid/qata`)
- Strategi: `git pull` langsung ke VPS — sederhana dan dapat diulang (repeatable)

---

## 7. Catatan Keamanan

### Yang Sudah Diterapkan
- Password di-hash dengan bcrypt
- Koneksi HTTPS via Cloudflare
- Registrasi dibatasi dengan invite code
- WAL mode pada SQLite untuk integritas data

### Catatan Repository
- Repository GitHub kini bersifat **publik**
- `SECRET_KEY` Flask telah dipindahkan ke **environment variable** (tidak lagi tersimpan di dalam kode sumber)

---

## 8. Insiden & Pelajaran

| Insiden | Penyelesaian |
|---|---|
| Konflik properti `is_active` pada flask-login | Diselesaikan dengan override properti di model User |
| Error format datetime | Diperbaiki di lapisan template Jinja2 |
| Error encoding SQLite | Ditangani di lapisan query |
| Korupsi database (7 postingan hilang) | Berhasil dipulihkan dari file database yang rusak |

---

## 9. Lingkungan Pengembangan Lokal

| Komponen | Detail |
|---|---|
| OS | Windows |
| Editor | Visual Studio Code |
| Python | 3.14 |
| Deployment lokal | Flask dev server |

---

*Dokumentasi ini mencerminkan kondisi platform per Juni 2026.*
