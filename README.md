# Dashboard-LLM — React Admin Dashboard Starter Template With Shadcn-ui

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://user-images.githubusercontent.com/9113740/201498864-2a900c64-d88f-4ed4-b5cf-770bcb57e1f5.png">
  <source media="(prefers-color-scheme: light)" srcset="https://user-images.githubusercontent.com/9113740/201498152-b171abb8-9225-487a-821c-6ff49ee48579.png">
</picture>

<div align="center"><strong>React Admin Dashboard Starter Template With Shadcn-ui</strong></div>
<div align="center">Built with Vite + React + TypeScript</div>
<br />
<div align="center">
<a href="https://react-shadcn-dashboard-starter.vercel.app/">View Demo</a>
</div>

---

Versi README ini diperbarui dan diperkaya untuk mencerminkan isi repository dashboard-llm, menambahkan panduan menjalankan di lokal dan di server (contoh deploy ke server Combiphar berbasis Linux/Docker), dokumentasi API, arsitektur sistem, dan daftar teknologi yang digunakan beserta rekomendasi best practice untuk production.

---

## Ringkasan Proyek

Dashboard-LLM adalah starter template admin dashboard berbasis React + TypeScript. Template ini menggabungkan:
- Komponen UI dari shadcn/ui (Radix + Tailwind)
- Manajemen data remote dengan TanStack Query (React Query)
- Table interaktif dengan TanStack Table
- Form handling dengan React Hook Form + Zod
- Contoh integrasi LLM melalui backend proxy (OpenAI atau penyedia LLM lain)

Tujuan: memberikan basis cepat untuk membangun aplikasi admin yang membutuhkan panel LLM (chat/summarize), tabel server-side, autentikasi sederhana, dan pattern produksi modern (linting, hooks, docker).

---

## Daftar Teknologi (Lengkap)

- Bahasa & Bundler
  - React 18 (Functional Components + Hooks)
  - TypeScript
  - Vite (dev server & build)
- UI / Styling
  - Tailwind CSS
  - shadcn/ui (components built on Radix)
  - Radix UI (base primitives)
- State & Data
  - TanStack Query (React Query) — async data fetching & caching
  - TanStack Table — tables, sorting, pagination
  - React Context — UI-level state (theme, auth)
- Form & Validation
  - React Hook Form
  - Zod (schema validation)
- Network / HTTP
  - Axios (HTTP client) — di client & server contoh
- Backend (opsional / template)
  - Node.js + Express (minimal proxy server example)
- Dev tooling & Quality
  - ESLint
  - Prettier
  - Husky (pre-commit hooks)
  - lint-staged
- CI / CD & Deployment
  - Docker, Nginx (example Dockerfile + nginx.conf)
  - Vercel / Netlify (frontend static)
  - Render / Heroku / Fly (backend)
- Ops & Infra (recommendasi)
  - PostgreSQL / MongoDB
  - Redis (cache / rate limit)
  - Prometheus / Grafana (metrics)
- LLM Providers (opsi)
  - OpenAI (Chat Completions / Responses API)
  - Anthropic, Llama2 via hosted API, atau self-hosted endpoints

---

## Struktur Project (apa yang ada di repo)

- src/
  - components/ — UI components, wrapper shadcn
  - pages/ — Dashboard, Students, Login, 404, LLM panel
  - hooks/ — useAuth, useLLM, useFetchStudents
  - services/ — auth.ts, students.ts, llm.ts
  - libs/ — react-query setup, theme provider
  - routes.tsx, main.tsx
- server/ (opsional)
  - routes/ — auth.js, students.js, llm.js
  - index.js
- public/ / static assets
- .env.example
- Dockerfile, nginx.conf
- README.md, package.json, tsconfig.json, vite.config.ts

Jika Anda tidak menemukan file tertentu di repo fork Anda, sesuaikan struktur atau buat file contoh berdasarkan template di README.

---

## Fitur Utama

- Autentikasi (login/signup) — token-based
- Dashboard utama dengan grafik (Recharts atau library lain)
- Halaman Students — TanStack Table dengan server-side pagination, searching, sorting
- Halaman LLM: chat/summarize, preview prompt & logs
- Mode Dark / Light
- 404 Not Found
- Contoh backend proxy LLM (Express) untuk menjaga secret API key di server

---

## Setup Lokal — Langkah demi langkah

Panduan ini mengasumsikan Anda memiliki Node.js (>=18 recommended), npm/yarn, dan git.

1. Clone repo
   ```
   git clone https://github.com/oemahsolution/dashboard-llm.git
   cd dashboard-llm
   ```

2. Install dependency (frontend)
   ```
   npm install
   ```
   atau
   ```
   yarn
   ```

3. Salin file env contoh
   ```
   cp .env.example .env
   ```
   Contoh isi minimal .env (frontend):
   ```
   VITE_API_BASE_URL=http://localhost:4000/api
   VITE_OPENAI_API_KEY=
   VITE_APP_ENV=development
   ```

   NOTE: Jangan taruh kunci LLM di file .env client. Gunakan backend proxy.

4. Menjalankan dev frontend
   ```
   npm run dev
   ```
   Buka: http://localhost:5173

5. (Opsional) Jika menggunakan backend lokal (server/)
   - Masuk ke folder server:
     ```
     cd server
     npm install
     cp .env.example .env
     ```
   - Isi server .env:
     ```
     OPENAI_API_KEY=sk-...
     PORT=4000
     ```
   - Jalankan server:
     ```
     npm run dev
     ```
   - Server akan berjalan di: http://localhost:4000
   - Frontend akan memanggil: http://localhost:4000/api/llm/...

6. Proxy Vite (opsional)
   Jika ingin proxy route API tanpa menggunakan absolute URL, tambahkan pada vite.config.ts:
   ```ts
   server: {
     proxy: {
       '/api': 'http://localhost:4000'
     }
   }
   ```

---

## Menjalankan di Server Combiphar (Contoh Deploy Produksi)

Petunjuk di bawah bersifat generik dan ditulis supaya bisa diterapkan pada server Combiphar berbasis Linux (Ubuntu) yang mendukung Docker. Jika tim infra Combiphar memiliki detail lain (user, firewall, reverse-proxy centralized, registries privat), sesuaikan langkahnya.

Pilihan A — Deploy dengan Docker (direkomendasikan)
1. Buat Docker image frontend:
   - Pastikan file Dockerfile ada (contoh ada di repo).
   - Build image (di mesin CI atau di server):
     ```
     docker build -t combiphar/dashboard-llm:latest .
     ```
2. Siapkan nginx.conf (disertakan di repo contoh) atau gunakan container nginx default. Jika ingin men-serve static:
   - Jalankan:
     ```
     docker run -d --name dashboard-llm -p 80:80 \
       -e VITE_API_BASE_URL=https://api.mycombiphar.internal/api \
       combiphar/dashboard-llm:latest
     ```
   - Atau gunakan docker-compose:
     ```yaml
     version: '3.8'
     services:
       frontend:
         image: combiphar/dashboard-llm:latest
         ports:
           - "80:80"
         environment:
           - VITE_API_BASE_URL=https://api.mycombiphar.internal/api
     ```
3. Backend (proxy) deploy:
   - Buat image backend (server/):
     ```
     cd server
     docker build -t combiphar/dashboard-llm-server:latest .
     ```
   - Jalankan backend container:
     ```
     docker run -d --name dashboard-llm-server -p 4000:4000 \
       -e OPENAI_API_KEY=sk-... \
       -e DATABASE_URL=postgres://user:pass@db:5432/dbname \
       combiphar/dashboard-llm-server:latest
     ```
4. Reverse proxy / TLS:
   - Jika Combiphar menggunakan Traefik / Nginx proxy, daftarkan route dan sertifikat TLS (Let's Encrypt internal or company CA).
   - Contoh Nginx config (reverse proxy):
     ```
     server {
       listen 443 ssl;
       server_name dashboard.mycombiphar.internal;

       ssl_certificate /etc/ssl/certs/...
       ssl_certificate_key /etc/ssl/private/...

       location / {
         proxy_pass http://127.0.0.1:80;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
     }
     ```

Pilihan B — Deploy tanpa Docker (instal Node + serve)
- Build frontend:
  ```
  npm run build
  ```
- Copy folder dist ke server (rsync / scp)
- Serve dengan nginx (letakkan dist di /var/www/dashboard-llm) dan konfigurasi nginx untuk static.
- Jalankan backend (server/) sebagai service systemd atau dengan process manager (pm2):
  ```
  pm2 start server/dist/index.js --name dashboard-llm-server --env production
  ```

Keamanan & Operasional di Combiphar:
- Pastikan API keys disimpan di Secrets Manager atau vault internal (Jenkins, HashiCorp Vault, AWS Secrets Manager)
- Gunakan network ACL / firewall untuk membatasi akses ke server backend
- Aktifkan monitoring & log forwarding (ELK, Datadog)
- Terapkan rate-limiting pada endpoint LLM

---

## Dokumentasi API (Detail / OpenAPI-like)

Base URL: {VITE_API_BASE_URL} (contoh: https://api.example.com/api)

Format umum error:
```
{
  "message": "Error description",
  "code": "ERR_CODE",
  "details": {...}
}
```

1) Auth
- POST /api/auth/signup
  - Body:
    ```
    { "name": string, "email": string, "password": string }
    ```
  - Response 201:
    ```
    { "user": { id, name, email }, "token": "<jwt>", "refreshToken": "<refresh>" }
    ```

- POST /api/auth/login
  - Body:
    ```
    { "email": string, "password": string }
    ```
  - Response 200:
    ```
    { "user": {...}, "token": "<jwt>", "refreshToken": "<refresh>" }
    ```

- POST /api/auth/refresh
  - Body:
    ```
    { "refreshToken": string }
    ```
  - Response 200:
    ```
    { "token": "<new_jwt>" }
    ```

2) Students
- GET /api/students
  - Query params: page (number), limit (number), q (search string), sort (e.g., name:asc)
  - Response 200:
    ```
    {
      "data": [ { "id", "name", "email", ... } ],
      "meta": { "total": number, "page": number, "limit": number }
    }
    ```

- GET /api/students/:id
  - Response 200:
    ```
    { "data": { ...student } }
    ```

- POST /api/students
  - Body: { name, email, ... }
  - Response 201: { "data": createdStudent }

- PUT /api/students/:id
  - Body: partial fields
  - Response 200: { "data": updatedStudent }

- DELETE /api/students/:id
  - Response 200: { "message": "deleted" }

3) LLM (Proxy)
- POST /api/llm/chat
  - Body:
    ```
    {
      "prompt": string,
      "options": {
        "model"?: string,
        "max_tokens"?: number,
        "temperature"?: number
      }
    }
    ```
  - Response 200:
    ```
    {
      "text": string,
      "meta": { "model": "...", "tokens_used"?: number }
    }
    ```

- POST /api/llm/summarize
  - Body:
    ```
    { "text": string }
    ```
  - Response 200:
    ```
    { "summary": string }
    ```

4) Logs (optional)
- GET /api/llm/logs
  - Query params: page, limit
  - Response 200:
    ```
    { "data": [ { "prompt", "response", "tokens", "userId", "createdAt" } ], "meta": {...} }
    ```

Auth:
- Protected endpoints harus mengharuskan header:
  ```
  Authorization: Bearer <token>
  ```

Rate limiting & Quota:
- Direkomendasikan untuk menambahkan header respons yang menjelaskan sisa quota/kebijakan rate-limit:
  - X-RateLimit-Limit
  - X-RateLimit-Remaining
  - X-RateLimit-Reset

---

## Contoh Implementasi: Client useLLM Hook & Server Proxy (Ringkasan)

Client hook (src/hooks/useLLM.ts):
```ts
import { useState } from "react";
import axios from "axios";

export function useLLM() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function queryLLM(prompt: string, options = {}) {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/llm/chat`, {
        prompt, options
      });
      setLoading(false);
      return res.data; // { text: "..." }
    } catch (e: any) {
      setLoading(false);
      setError(e?.response?.data?.message || e.message);
      throw e;
    }
  }

  return { queryLLM, loading, error };
}
```

Server (server/routes/llm.js — contoh ringkas)
```js
const express = require("express");
const router = express.Router();
const axios = require("axios");
const rateLimit = require("express-rate-limit");

const limiter = rateLimit({ windowMs: 60 * 1000, max: 20 }); // contoh

router.post("/chat", limiter, async (req, res) => {
  const { prompt, options } = req.body;
  if (!prompt) return res.status(400).json({ message: "Prompt required" });

  try {
    const apiKey = process.env.OPENAI_API_KEY;
    const payload = {
      model: options?.model || "gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      max_tokens: options?.max_tokens || 800,
    };

    const openAIRes = await axios.post(
      "https://api.openai.com/v1/chat/completions",
      payload,
      { headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" } }
    );

    const text = openAIRes.data?.choices?.[0]?.message?.content || "";
    res.json({ text, meta: { model: payload.model } });
  } catch (err) {
    console.error(err?.response?.data || err.message);
    res.status(500).json({ message: "LLM provider error", detail: err.message });
  }
});

module.exports = router;
```

Keamanan:
- Jangan expose OPENAI_API_KEY ke client.
- Terapkan rate-limiting, input validation (Zod), logging, sanitasi.

---

## Best Practices & Production Checklist

- [ ] Pastikan tidak ada API keys atau secret di repo.
- [ ] Gunakan Vault / Secret Manager untuk menyimpan secrets.
- [ ] Terapkan TLS dan HTTP security headers.
- [ ] Rate limiting pada endpoint LLM untuk kontrol biaya.
- [ ] Batasi max_tokens dan pilih model yang sesuai budget.
- [ ] Mask sensitive data di logs.
- [ ] Monitoring & alerts di tempat (uptime, error rates, token usage).
- [ ] Backup database & recovery plan.
- [ ] Pen-test & input sanitization untuk mencegah injection / abuse.
- [ ] Lakukan audit biaya LLM secara berkala.

---

## Troubleshooting (Ringkasan)

1. Dev server tidak jalan:
   - Cek versi Node (>=16/18 direkomendasikan).
   - Hapus node_modules & reinstall:
     ```
     rm -rf node_modules package-lock.json
     npm install
     ```

2. Env variabel tidak terbaca:
   - Vite memerlukan prefix VITE_ untuk variabel client.
   - Restart dev server setelah ubah .env.

3. CORS error:
   - Pastikan backend mengizinkan origin dev (http://localhost:5173) atau gunakan proxy vite.

4. 401 Unauthorized:
   - Pastikan token di simpan & dikirim di header Authorization.
   - Cek mekanisme refresh token.

5. LLM provider error:
   - Cek keys, rate limits, model name, payload size.

6. Build CI/CD gagal:
   - Pastikan env vars di CI diset.
   - Pastikan Node versi di runner sesuai.
   - Cek scripts lint/format.

---

## Contoh .env.example

Buat file .env.example di root (contoh):
```
# Frontend
VITE_API_BASE_URL=http://localhost:4000/api
VITE_APP_ENV=development

# Do NOT store production OPENAI key here if the file is committed
# Only for local dev/testing with backend proxy
VITE_OPENAI_API_KEY=
```

Contoh server/.env.example:
```
PORT=4000
OPENAI_API_KEY=sk-...
DATABASE_URL=postgres://user:pass@localhost:5432/db
JWT_SECRET=changeme
```

---

## Contribution

- Buat issue untuk fitur/bug.
- Fork repo, buat branch feature/<nama>, buat PR.
- Gunakan Husky & lint-staged: pastikan linting/format lulus sebelum push.
- Sertakan deskripsi runbook / testing steps pada PR.

---

## Lisensi

Project ini mengikuti lisensi sesuai file LICENSE pada repository. Periksa sebelum penggunaan komersial.

---
