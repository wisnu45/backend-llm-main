# Combiphar Chatbot Frontend — VITA

Selamat datang di **Combiphar Chatbot Frontend (VITA)**, solusi antarmuka modern untuk chatbot berbasis AI yang mendukung proses interaksi, sinkronisasi dokumen, serta integrasi dengan API backend canggih. Proyek ini dibangun dengan teknologi web terkini untuk memenuhi kebutuhan enterprise, skalabilitas, dan kemudahan pengembangan.
[View Dashboard Chatbot AI VITA](https://combiphar-chatbot.oemahsolution.com/)

---

## 1. Architecture Overview

Arsitektur VITA Chatbot mengadopsi pola **microservices** berbasis frontend-backend terpisah, dengan komunikasi melalui REST API dan WebSocket (opsional untuk streaming). Diagram arsitektur tinggi:

```
┌───────────────┐        ┌────────────────────────┐       ┌───────────────┐
│   User        │◄──────►│ Combiphar Frontend VITA│◄─────►│ Chatbot API   │
└───────────────┘        │ (React, TS, Tailwind) │       │ (OpenAI,      │
                         └────────────────────────┘       │ Custom Logic) │
                               ▲         │                └───────────────┘
                               │         │
                 ┌─────────────┴───┐   ┌─┴─────────────┐
                 │ Document Sync   │   │ Auth Service  │
                 │ (API, polling) │   │ (JWT, OAuth2) │
                 └────────────────┘   └───────────────┘
```

- **Frontend (VITA)**: React (TypeScript), Tailwind, shadcn/ui, TanStack Query.
- **Backend (API Chatbot)**: Node.js/Express, OpenAI API, Sinkronisasi dokumen dan user.
- **Document Sync**: Sinkronisasi metadata dan konten dokumen dari sumber eksternal ke backend.
- **Auth Service**: Token-based authentication (JWT/OAuth2).

---

## 2. Document Synchronization Flow

Proses sinkronisasi dokumen melibatkan beberapa tahap:

1. **Inisiasi Sinkronisasi**  
   Pengguna/admin memicu sinkronisasi via frontend (tombol/command).
2. **Entri Sinkronisasi**  
   Frontend mengirim request ke endpoint `/api/documents/sync` pada backend.
3. **Proses Backend**  
   Backend melakukan fetch dokumen dari sumber eksternal (database/API/file storage), memvalidasi, dan menyimpan ke database internal.
4. **Update Status**  
   Backend mengirim respon status sinkronisasi (`pending`, `success`, `failed`) ke frontend.
5. **Feedback UI**  
   Frontend menampilkan progres, hasil, dan log sinkronisasi pada dashboard admin.
6. **Notifikasi**  
   Notifikasi (real-time/async) untuk status sukses/gagal menggunakan WebSocket atau polling.

Contoh alur request:

```
POST /api/documents/sync
Body: { source: "knowledge_base", userId: "..." }
Response: { status: "success", synced: 12, errors: [] }
```

---

## 3. Quick Start

### Prasyarat

- Node.js >= 18
- npm atau yarn
- Docker (opsional)
- Git

### Instalasi

1. **Clone Repository**

   ```sh
   git clone https://github.com/oemahsolution/combiphar-chatbot-frontend.git
   cd combiphar-chatbot-frontend
   ```

2. **Install Dependencies**

   ```sh
   npm install
   # atau
   yarn
   ```

3. **Konfigurasi Environment**
   Salin dan isi file `.env.example`:

   ```sh
   cp .env.example .env
   ```

   Contoh minimal `.env`:

   ```
   VITE_API_BASE_URL=https://api-chatbot.oemahsolution.com/api
   VITE_APP_ENV=development
   ```

4. **Jalankan Dev Server**

   ```sh
   npm run dev
   ```

   Akses di: [http://localhost:5173](http://localhost:5173)

5. **Integrasi dengan API Backend**
   Pastikan API backend berjalan di `https://api-chatbot.oemahsolution.com` dan endpoint sesuai dokumentasi.

---

## 4. Docker Configuration

### Build & Deploy Frontend dengan Docker

1. **Build Docker Image**

   ```sh
   docker build -t combiphar/vita-frontend:latest .
   ```

2. **Jalankan Container**

   ```sh
   docker run -d --name vita-frontend -p 80:80 \
     -e VITE_API_BASE_URL=https://api-chatbot.oemahsolution.com/api \
     combiphar/vita-frontend:latest
   ```

3. **Contoh docker-compose.yml**

   ```yaml
   version: '3.8'
   services:
     frontend:
       image: combiphar/vita-frontend:latest
       ports:
         - '80:80'
       environment:
         - VITE_API_BASE_URL=https://api-chatbot.oemahsolution.com/api
   ```

4. **Reverse Proxy (Nginx)**

   ```
   server {
     listen 443 ssl;
     server_name combiphar-chatbot.oemahsolution.com;

     ssl_certificate /etc/ssl/certs/combiphar.pem;
     ssl_certificate_key /etc/ssl/private/combiphar.key;

     location / {
       proxy_pass http://127.0.0.1:80;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     }
   }
   ```

---

## 5. API Documentation

Dokumentasi API lengkap tersedia di:  
[https://api-chatbot.oemahsolution.com/apidocs/#/](https://api-chatbot.oemahsolution.com/apidocs/#/)

### Contoh Endpoint Utama

- **POST /api/chat**  
  Kirim prompt/chat untuk AI.
- **GET /api/documents**  
  Ambil daftar dokumen sinkronisasi.
- **POST /api/documents/sync**  
  Trigger sinkronisasi dokumen.
- **POST /api/auth/login**  
  Autentikasi user.

#### Autentikasi

Semua endpoint protected wajib menyertakan header:

```
Authorization: Bearer <token>
```

---

## 6. Project Structure

```
combiphar-chatbot-frontend/
├── src/
│   ├── components/     # UI Components (chat, document, admin dashboard)
│   ├── pages/          # Page-level views (Chat, Documents, Login, 404)
│   ├── hooks/          # Custom hooks (useChat, useSync, useAuth)
│   ├── services/       # API calls (auth, chat, documents)
│   ├── libs/           # Utility libraries (query setup, theme provider)
│   ├── routes.tsx      # Routing config
│   ├── main.tsx        # Entry point
├── public/             # Static files
├── .env.example        # Contoh env vars
├── Dockerfile          # Docker config
├── nginx.conf          # Reverse proxy config (optional)
├── README.md           # Dokumentasi ini
├── package.json        # Dependency manifest
├── tsconfig.json       # TypeScript config
├── vite.config.ts      # Vite bundler config
```

---

## 7. Development

- **Linting & Formatting:**
  ```
  npm run lint
  npm run format
  ```
- **Testing:**  
  (Tambahkan test sesuai kebutuhan, rekomendasi: Jest/Testing Library)
- **Pre-commit Hooks:**  
  Husky & lint-staged untuk menjaga kualitas kode.
- **Hot Reload:**  
  Vite mendukung hot reload out-of-the-box.

### Workflow Pengembangan

1. Buat branch feature/bugfix
2. Commit dengan deskripsi yang jelas
3. Push branch, buat Pull Request
4. Pastikan linting dan format lulus sebelum merge

---

## 8. Troubleshooting

1. **Dev server gagal berjalan**
   - Cek versi Node (>=18)
   - Hapus node_modules & reinstall:
     ```
     rm -rf node_modules package-lock.json
     npm install
     ```
2. **Env variable tidak terbaca**
   - Pastikan prefix `VITE_` untuk frontend.
   - Restart dev server setelah ubah .env.
3. **CORS error**
   - Pastikan backend mengizinkan origin frontend, atau gunakan proxy di vite.config.ts.
4. **401 Unauthorized**
   - Pastikan token dikirim di header Authorization.
   - Cek refresh token.
5. **Docker build fails**
   - Pastikan context build benar, dependency terinstall, port expose sesuai.

---

## 9. Monitoring & Logs

### Frontend

- Gunakan service monitoring:
  - Vercel/Netlify: built-in analytics & logs
  - Nginx: akses log dan error log di server

### Backend

- Pantau API logs (lihat dokumentasi backend)
- Integrasi monitoring: ELK, Grafana, Datadog, Sentry

### Healthcheck

- Endpoint `/api/health` untuk pengecekan status
- Aktifkan alert pada error rate tinggi, rate limit terlampaui

---

## 10. Deployment

### Production (Linux Server/Docker)

1. **Build frontend**
   ```
   npm run build
   ```
2. **Deploy ke server:**
   - Salin folder `dist/` ke server
   - Serve dengan Nginx atau Docker
3. **Jalankan backend sesuai petunjuk API**
4. **Konfigurasi domain dan SSL/TLS**
5. **Pantau logs & monitoring**

### Tips Operasional

- Simpan secrets di Vault/Secrets Manager (jangan di git)
- Aktifkan firewall & network ACL
- Gunakan rate-limiting pada endpoint AI
- Backup database secara berkala
- Audit penggunaan API & biaya LLM

---

## Resources

- [Frontend Live Demo](https://combiphar-chatbot.oemahsolution.com/)
- [API Docs](https://api-chatbot.oemahsolution.com/apidocs/#/)

---

## Contribution

- Fork repo, buat branch, ajukan PR.
- Sertakan deskripsi runbook/testing.
- Buat issue untuk bug/fitur baru.

---

## License

Periksa file LICENSE di repository untuk detail lisensi penggunaan.

---
