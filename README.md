# Qata

Platform blogging minimalis yang berfokus pada ketenangan tulisan dan kenyamanan membaca. Dibangun dengan Python dan Flask.

**[qata.my.id](https://qata.my.id)**

---

## Filosofi

Qata dirancang dengan satu prinsip utama: **tulisan adalah yang utama**. 
Tidak ada iklan komersial, tidak ada pelacak pihak ketiga (*third-party trackers*), dan tidak ada kerumitan visual yang mendistraksi. Hanya penulis, ide yang dituangkan, dan pembaca.

---

## Fitur Utama

### 1. Pendaftaran Fleksibel & Terproteksi
- **Mode Pendaftaran Dinamis:** Administrator dapat mengubah mode registrasi kapan saja melalui Panel Admin:
  - **Terbuka (*Open*):** Pengguna baru dapat mendaftar langsung tanpa kode undangan.
  - **Hanya Undangan (*Invite Only*):** Pendaftaran mewajibkan kode undangan sekali pakai (maksimal 5 kode per pengguna).
  - **Ditutup (*Closed*):** Pendaftaran ditutup sementara saat terjadi lonjakan bot atau pemeliharaan.
- **Proteksi Anti-Bot Berlapis:** Formulir pendaftaran dilengkapi kolom jebakan (*honeypot*), pertanyaan keamanan matematika dinamis, dan pembatasan frekuensi (*rate limiting*) berbasis IP hash.

### 2. Editor & Manajemen Konten
- **Editor Markdown:** Antarmuka penulisan teks Markdown yang bersih, responsif, dan bebas gangguan.
- **Upload & Kompresi Gambar:** 
  - Penulis yang memiliki izin dapat menyisipkan ilustrasi gambar ke dalam artikel.
  - Gambar diproses otomatis di server menggunakan **Pillow**: rotasi orientasi kamera (EXIF), *auto-resize* proporsional ke lebar maksimal 1200px, dan dikonversi ke format **WebP** terkompresi (kualitas 82) sehingga ukuran berkas sangat ringan (<100 KB) tanpa mengurangi kejernihan.
  - Terisolasi rapi di folder masing-masing pengguna (`/static/uploads/<username>/`).
- **Kontrol Izin Gambar (Persiapan Monetisasi):** Administrator dapat mengaktifkan atau menonaktifkan kemampuan unggah gambar untuk setiap pengguna secara individual langsung dari tabel Panel Admin.

### 3. Tampilan & Desain
- **4 Pilihan Tema:** Tersedia tema **Terang** (*Light*), **Gelap** (*Dark*), **Sepia**, dan **Hutan** (*Forest*) yang dapat dipilih pengguna di profil. Tema blog publik akan otomatis mengikuti preferensi pemilik blog.
- **Tipografi Lokal Mandiri (*Self-hosted Fonts*):** Menggunakan font *Literata* dan *IBM Plex Sans* berformat `.woff2` yang disimpan langsung di server lokal. Zero request ke Google Fonts, privasi terjaga, dan pemuatan halaman instan.
- **Tata Letak Adaptif:** Format kontainer bacaan berukuran optimal (680px) dengan tipografi proporsional, pembatas gambar responsif, serta tabel yang rapi di layar desktop maupun ponsel pintar.

### 4. Keamanan & Akun
- **Proteksi Brute-Force Login:** Pembatasan percobaan login (maksimal 5 kali salah per username atau 20 kali salah per IP dalam 15 menit) untuk menangkal serangan kamus/otomasi.
- **Kompatibilitas Real-IP:** Mendukung reverse-proxy Cloudflare (`CF-Connecting-IP`) dan Nginx `ProxyFix`.
- **Manajemen Password:**
  - Administrator dapat mereset password pengguna secara instan dengan satu klik (menghasilkan password acak yang aman).
  - Penulis dapat mengganti password mereka secara mandiri dari menu profil dashboard.
- **Hashing Aman:** Seluruh password diamankan dengan algoritma `bcrypt`.

### 5. Halaman Publik & SEO
- **Halaman Penulis:** Blog per pengguna (`qata.my.id/<username>`), arsip tahunan (`/<username>/arsip`), dan halaman profil (`/<username>/tentang`).
- **Halaman Kustom:** Pengguna dapat membuat halaman bebas tersendiri (`/<username>/<slug>`).
- **RSS Feed:** Umpan sindikasi XML otomatis untuk setiap penulis (`/<username>/rss`).
- **Sistem Like Tanpa Akun:** Pembaca dapat mengapresiasi tulisan tanpa login, dengan pencegahan duplikasi like menggunakan hash IP SHA-256 lokal.
- **Sitemap & Robots Dinamis:** Berkas `sitemap.xml` diperbarui otomatis oleh sistem setiap kali tulisan diterbitkan, diubah, atau dihapus, mempermudah pengindeksan oleh mesin pencari secara akurat.

### 6. Administrasi & Donasi
- **Monitoring Status Server:** Pemantauan metrik sumber daya server VPS secara *real-time* (penggunaan CPU, RAM, Disk, Swap, dan *Uptime*).
- **Health Check Eksternal:** Pengecekan otomatis latensi dan ketersediaan layanan web pendukung (`sdmfsrd.web.id`).
- **Editor Beranda:** Administrator dapat menyunting judul, deskripsi, fitur, dan teks panggilan aksi (*CTA*) landing page langsung dari dashboard.
- **Dukungan & Donasi QRIS:** Halaman donasi sukarela terintegrasi dengan kode QRIS dan fitur salin nomor NMID untuk mendukung biaya operasional dan kelangsungan server.

---

## Tech Stack

- **Backend:** Python 3.10+ & Flask
- **Database:** SQLite3 (WAL mode untuk konkurensi cepat)
- **Template Engine:** Jinja2
- **Markdown Parser:** Mistune (ekstensi tabel & coret teks)
- **Pengolah Gambar:** Pillow (PIL)
- **Otentikasi:** Flask-Login + bcrypt
- **Metrik Sistem:** psutil + requests
- **Server Produksi:** Gunicorn + Nginx (Reverse Proxy & Static Cache)
- **DNS / SSL:** Cloudflare (Edge SSL & CDN)

---

## Kenapa Qata Ringan dan Cepat?

1. **Zero JS Framework:** Seluruh antarmuka dirender di sisi server (*Server-Side Rendering* / SSR) dengan HTML dan CSS murni.
2. **Font Lokal:** Tidak ada dependensi font eksternal. Font `.woff2` dikirim langsung dengan kompresi tingkat tinggi.
3. **Markdown Di-render Saat Disimpan:** Konten Markdown di-parse ke HTML saat disimpan ke database, sehingga waktu baca (*reading time*) dan pembacaan artikel berlangsung seketika tanpa overhead komputasi.
4. **Optimasi Gambar Otomatis:** Gambar yang diunggah dikompresi ke WebP berukuran kecil, menghemat konsumsi *bandwidth* server dan kuota pengunjung.
5. **Privasi Total:** Tidak ada skrip analitik eksternal, Google Analytics, atau piksel pelacak.

---

## Instalasi Lokal

```bash
# 1. Clone repositori
git clone https://github.com/andriawekh-droid/qata.git
cd qata

# 2. Buat & aktifkan virtual environment
python -m venv venv
venv\Scripts\activate       # Windows PowerShell / CMD
# source venv/bin/activate  # Linux / macOS

# 3. Install dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi pengembangan
python app.py
```

Buka peramban Anda di `http://127.0.0.1:5000`.

---

## Deployment di VPS

Qata berjalan optimal di VPS Ubuntu (spesifikasi minimum: 1 vCPU, 1 GB RAM):

- **Aplikasi:** Dikelola oleh systemd service (`qata.service`) yang menjalankan Gunicorn di socket lokal `127.0.0.1:8000`.
- **Nginx:** Menangani reverse proxy, pengiriman berkas statis (`/static`), `robots.txt`, dan `sitemap.xml`.
- **Cloudflare:** Menyediakan perlindungan DDoS, DNS, SSL otomatis, dan caching aset statis dengan versioning (`?v=X`).

Perintah pembaruan cepat di server:
```bash
cd /var/www/qata
sudo git pull origin main
sudo systemctl restart qata
```

---

## Lisensi

Didistribusikan di bawah lisensi MIT. Bebas digunakan, dipelajari, dan dimodifikasi.

---

Dibuat dengan tenang oleh **[awekh](https://qata.my.id/awekh)**.
