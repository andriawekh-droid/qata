# Panduan Setup Subdomain `username.qata.blog` di Cloudflare & VPS

Dokumen ini menjelaskan langkah demi langkah mengaktifkan subdomain otomatis untuk pengguna Qata Premium (`username.qata.blog`) setelah kode terbaru ditarik (*pull*) ke VPS.

> **Catatan keamanan:** Secara bawaan fitur subdomain nonaktif (`QATA_SUBDOMAIN_ENABLED=0`) agar situs `qata.blog` tetap normal sebelum DNS, SSL Wildcard, dan Nginx selesai dikonfigurasi. Aktifkan `QATA_SUBDOMAIN_ENABLED=1` di langkah terakhir.

---

## 1. Setup DNS Wildcard di Cloudflare

1. Masuk ke dashboard **Cloudflare** dan pilih domain **`qata.blog`**.
2. Buka menu **DNS → Records**.
3. Pastikan record utama sudah ada:
   * `A` | `@` | `<IP_VPS_ANDA>` | **Proxied** (awan oranye)
   * `A` (atau `CNAME`) | `www` | `<IP_VPS_ANDA>` (atau `qata.blog`) | **Proxied**
4. Klik **Add record** untuk menambahkan wildcard subdomain:
   * **Type**: `A`
   * **Name**: `*`
   * **IPv4 address**: `<IP_VPS_ANDA>` (sama persis dengan record `@`)
   * **Proxy status**: **Proxied** (awan oranye aktif)
   * **TTL**: `Auto`
5. Simpan (*Save*).
6. Buka menu **SSL/TLS → Overview** dan pastikan mode enkripsi diset ke **Full (strict)**.

> **Catatan Cloudflare Free Plan:** Proxy wildcard (`*`) sudah didukung gratis oleh Cloudflare pada DNS dan SSL Edge untuk subdomain 1 tingkat (`nama.qata.blog`).

---

## 2. Setup Wildcard SSL di VPS

Pilih **salah satu** opsi di bawah ini (Opsi A paling praktis karena tidak perlu setup API token Certbot).

### Opsi A (Direkomendasikan): Cloudflare Origin Certificate

1. Di dashboard Cloudflare, buka **SSL/TLS → Origin Server** → klik **Create Certificate**.
2. Pastikan setting:
   * **Private key type**: `RSA (2048)`
   * **Hostnames**: `qata.blog`, `*.qata.blog` (biasanya sudah terisi otomatis)
   * **Certificate Validity**: `15 years`
3. Klik **Create**.
4. Di VPS, buat folder dan simpan kedua file sertifikat tersebut:
   ```bash
   sudo mkdir -p /etc/ssl/cloudflare
   sudo nano /etc/ssl/cloudflare/qata.blog.pem
   # Tempel (paste) isi "Origin Certificate", simpan & keluar

   sudo nano /etc/ssl/cloudflare/qata.blog.key
   # Tempel (paste) isi "Private Key", simpan & keluar

   sudo chmod 600 /etc/ssl/cloudflare/qata.blog.key
   ```

### Opsi B (Alternatif): Let's Encrypt Wildcard via Certbot DNS-Cloudflare

Jika ingin sertifikat Let's Encrypt langsung (misal tidak ingin bergantung pada Origin CA):

```bash
sudo apt update
sudo apt install -y python3-certbot-dns-cloudflare
```

Buat API Token Cloudflare dengan izin `Zone:DNS:Edit` untuk `qata.blog`, simpan di `/etc/letsencrypt/cloudflare.ini`:
```ini
dns_cloudflare_api_token = TOKEN_CLOUDFLARE_ANDA
```
```bash
sudo chmod 600 /etc/letsencrypt/cloudflare.ini
sudo certbot certonly --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d qata.blog -d '*.qata.blog'
```

---

## 3. Konfigurasi Nginx

Edit virtual host Nginx untuk Qata (misalnya `/etc/nginx/sites-available/qata.blog` atau sesuaikan dengan nama berkas konfigurasi Anda):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name qata.blog www.qata.blog *.qata.blog;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name qata.blog www.qata.blog *.qata.blog;

    # Jika memakai Opsi A (Cloudflare Origin Certificate):
    ssl_certificate     /etc/ssl/cloudflare/qata.blog.pem;
    ssl_certificate_key /etc/ssl/cloudflare/qata.blog.key;

    # Jika memakai Opsi B (Let's Encrypt):
    # ssl_certificate     /etc/letsencrypt/live/qata.blog/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/qata.blog/privkey.pem;

    # Izinkan upload gambar artikel & bukti transfer (maksimal 10 MB + overhead)
    client_max_body_size 15M;

    location / {
        proxy_pass http://127.0.0.1:8000; # sesuaikan port/socket gunicorn Qata
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Uji dan reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 4. Pull Kode & Aktifkan di Service Systemd Qata

1. Tarik perubahan terbaru di folder proyek Qata di VPS:
   ```bash
   cd /path/to/qata
   git pull origin main
   ```
   *(Tidak perlu migrasi SQL manual — `init_db()` otomatis menambah kolom `is_premium`, `premium_since`, dan tabel `payments` saat aplikasi start.)*

2. Edit file service systemd Qata (misal `/etc/systemd/system/qata.service`), tambahkan environment variable di bagian `[Service]`:
   ```ini
   Environment="QATA_BASE_DOMAIN=qata.blog"
   Environment="QATA_SUBDOMAIN_ENABLED=1"
   ```

3. Terapkan dan restart service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart qata
   sudo systemctl status qata
   ```

---

## 5. Daftar Periksa Pengujian

Setelah service restart, pastikan hal berikut berjalan normal:

- [ ] `https://qata.blog` terbuka normal, halaman Jelajahi, Masuk, dan Dashboard berfungsi.
- [ ] `https://www.qata.blog` otomatis redirect `301` ke `https://qata.blog`.
- [ ] Akun **Admin** atau **Premium** (mis. `https://awekh.qata.blog`) langsung menampilkan halaman blog pengguna; URL lama `https://qata.blog/awekh` otomatis redirect `301` ke `https://awekh.qata.blog/`.
- [ ] Akun **Gratis** jika diakses lewat `<user>.qata.blog` otomatis diarahkan ke `https://qata.blog/<user>`.
- [ ] Halaman **Dashboard → Premium & Donasi** bisa mengunggah bukti transfer QRIS dan muncul di **Panel Admin → Verifikasi Pembayaran**.
- [ ] Saat admin klik **Verifikasi** pada pengajuan Premium, akun langsung menjadi Premium (`can_upload_image = 1`, `is_premium = 1`) dan subdomain `username.qata.blog` langsung aktif.
