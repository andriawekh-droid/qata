# Blueprint Teknis — Qata (qata.blog)

Dokumen ini merangkum keputusan teknis platform Qata agar bisa dipakai ulang sebagai referensi saat membangun aplikasi lain yang serupa (web app monolitik, ringan, self-hosted).

## 1. Filosofi Produk
- "Calm Internet": tanpa gangguan, minimalis, fokus ke konten teks.
- Invite-only, tanpa tracker eksternal, menghormati privasi pengguna.

## 2. Stack Teknologi
| Komponen         | Pilihan                         |
|------------------|----------------------------------|
| Backend          | Python 3.10+ & Flask (SSR monolitik) |
| Database         | SQLite3 (mode WAL)               |
| Template engine  | Jinja2                           |
| Markdown parser  | Mistune                          |
| Pengolah gambar  | Pillow (PIL)                     |
| Auth             | Flask-Login + bcrypt             |
| Metrik sistem    | psutil                           |
| App server       | Gunicorn                         |
| Reverse proxy    | Nginx                            |
| SSL/DNS/CDN      | Cloudflare (mode Full Strict)    |
| OS Server        | Ubuntu 22.04 VPS                 |
| Dev lokal        | Windows + VS Code                |

## 3. Keputusan Desain Kunci
- Mendukung upload gambar untuk pengguna berizin/premium dengan kompresi otomatis ke format WebP (lebar maks 1200px) via Pillow, terisolasi di `/static/uploads/<username>/`.
- Mode pendaftaran dinamis (*Open*, *Invite Only* dengan maksimal 5 kode undangan sekali pakai per user non-admin, atau *Closed*).
- URL berbasis path: `domain.com/username/slug`.
- Like/reaksi disimpan via hash IP SHA-256 (bukan IP mentah) untuk privasi.
- Dukungan dwibahasa antarmuka: Bahasa Indonesia & Inggris (`i18n.py`).
- Estetika minimal dengan 4 tema (Light, Dark, Sepia, Forest) dan tipografi lokal mandiri (*self-hosted* `.woff2`: Literata & IBM Plex Sans).

## 4. Struktur File & Deployment
- Repo publik di GitHub, `SECRET_KEY` Flask disimpan sebagai environment variable, bukan hardcode di kode.
- Autentikasi VPS ke GitHub via SSH key (ed25519) terpisah.
- Alur deploy standar:
  1. `git add . && git commit && git push` (lokal)
  2. Backup dulu di VPS: jalankan script backup
  3. `git pull` di VPS
  4. `systemctl restart <nama-service>`

## 5. Backup & Database
- **Penting:** SQLite mode WAL menyimpan perubahan di file `-wal` dan tidak otomatis "checkpoint" ke file database utama. Backup dengan `cp` biasa bisa menangkap data basi/beku.
- Solusi: jalankan `PRAGMA wal_checkpoint(TRUNCATE)` sebelum backup, atau pakai SQLite `.backup` API.
- Aliran data hanya boleh **VPS → lokal** (untuk inspeksi), jangan pernah sebaliknya (`scp` database lokal ke VPS berisiko menimpa data live yang lebih baru).
- Folder `instance/` (tempat file database) **wajib** selalu ada di `.gitignore` — kalau file ini ke-track Git lalu ada revert, data live bisa hilang.

## 6. Caching & Aset Statis
- Cloudflare cache aset statis (CSS/JS) sampai 30 hari.
- Solusi: gunakan versioned query string saat update, contoh: `style.css?v=2`.

## 7. Catatan Reuse untuk Proyek Lain
Pola-pola di atas (terutama struktur invite-only, SQLite+WAL backup, dan deployment flow) bisa langsung dipakai ulang untuk aplikasi web monolitik lain yang butuh:
- Skala kecil-menengah, single VPS.
- Privasi pengguna sebagai prioritas.
- Biaya infrastruktur rendah (tanpa layanan cloud mahal).
