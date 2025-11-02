# React Admin Dashboard Starter Template With Shadcn-ui (Dashboard-LLM)

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

## Ringkasan Proyek

Dashboard-LLM adalah starter template admin dashboard berbasis React + TypeScript yang dilengkapi komponen Shadcn-ui, TailwindCSS, dan integrasi fitur-fitur umum (auth, tabel, grafik). Versi ini ditambahkan panduan untuk men-deploy, arsitektur sistem, troubleshooting, setup dashboard untuk bekerja dengan LLM (Large Language Model) dan dokumentasi API.

## Teknologi yang Digunakan

- Bahasa & Framework:
  - React 18 + TypeScript
  - Vite (build & dev server)
- Styling & UI:
  - Tailwind CSS
  - Shadcn-ui (komponen UI, desain system dengan Radix)
- State & Data:
  - React Query (TanStack Query) — async state management
  - TanStack Table — table rendering dan server-side features
  - React Hook Form + Zod — form handling & validation
- Build / Quality:
  - ESLint
  - Prettier
  - Husky (pre-commit hooks)
- Lain-lain / Ops:
  - Axios / fetch — HTTP client
  - dotenv — env var handling
  - Docker (opsional untuk container)
- Integrasi LLM:
  - OpenAI (atau model LLM self-hosted via API)
  - Simple server layer (Node/Express atau serverless) untuk proxy & rate-limiting (disarankan)

---

## Fitur Utama
- Authentication (sederhana) — login/signup halaman
- Dashboard utama dengan grafik (Recharts) dan ringkasan KPI
- Halaman Students — TanStack Table dengan server-side pagination, searching, sorting
- 404 Not Found page
- Mode gelap / terang
- Contoh integrasi Dashboard-LLM:
  - Panel tanya jawab / summarization menggunakan LLM
  - Preview prompt & logs

---

## Arsitektur Sistem

Keterangan arsitektur di-level tinggi:

- Client (React, Vite)
  - UI: Shadcn-ui + Tailwind
  - State: React Query untuk remote data, React Context untuk UI state (theme, auth token)
  - Routes: React Router
  - Dashboard LLM UI: Komponen untuk input prompt, history, streaming results (jika didukung)

- API Layer (Backend / Proxy)
  - Endpoint REST / GraphQL untuk:
    - Auth (login/signup, token refresh)
    - CRUD data (students, reports, settings)
    - LLM proxy endpoints (/api/llm/chat, /api/llm/summarize)
  - Validasi request & rate limiting
  - Menyimpan log prompt dan respons (opsional)
  - Menghubungkan ke provider LLM (OpenAI, Anthropic, Llama2 via API endpoint, dll.)

- Storage
  - Database (Postgres / MongoDB) untuk user, students, logs
  - Optional: Redis for caching, job queue

- Deployment
  - Frontend: Vercel / Netlify / Static hosting (build -> dist)
  - Backend: Node on Heroku / Render / Fly / Serverless (AWS Lambda, Cloud Functions)
  - Optional: Docker + Kubernetes

Diagram singkat (text):
Client (React) <--> Backend API (Node/Express) <--> LLM provider (OpenAI/External)  
                              |
                              -> Database (Postgres/MongoDB)
                              -> Cache (Redis)

---

## Struktur Direktori (Contoh)
- src/
  - components/ (ui components, shadcn wrappers)
  - pages/ (Dashboard, Students, Login, 404)
  - hooks/ (useAuth, useLLM, useFetchStudents)
  - services/ (api clients: auth.ts, students.ts, llm.ts)
  - libs/ (react-query setup, theme provider)
  - routes.tsx
  - main.tsx
- server/ (opsional: backend proxy)
  - routes/
    - auth.js
    - students.js
    - llm.js
  - index.js
- .env
- Dockerfile
- README.md

---

## Setup Lokal (Getting Started)

1. Clone repo:
   ```
   git clone https://github.com/oemahsolution/dashboard-llm.git
   cd dashboard-llm
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Salin file env contoh:
   ```
   cp .env.example .env
   ```

4. Isi konfigurasi .env (contoh minimal):
   ```
   VITE_API_BASE_URL=http://localhost:4000/api
   VITE_OPENAI_API_KEY=sk-...
   VITE_APP_ENV=development
   ```

5. Jalankan dev server:
   ```
   npm run dev
   ```
   Buka http://localhost:5173

Jika ada backend lokal:
- Masuk ke folder server dan jalankan:
  ```
  cd server
  npm install
  npm run dev
  ```
  Server akan berjalan mis. pada http://localhost:4000

---

## Deployment

Opsi cepat (frontend only):
- Build:
  ```
  npm run build
  ```
- Deploy hasil folder dist ke Vercel, Netlify, atau static hosting.

Opsi penuh (frontend + backend):
- Deploy backend ke provider (Render / Heroku / Fly)
- Pastikan env variable (OPENAI key, DB URL) diset di env pada provider
- Set VITE_API_BASE_URL pada frontend ke URL backend
- Build & deploy frontend

Contoh Docker (frontend):
Dockerfile sederhana
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Code: Dashboard LLM Setup (Client + Minimal Server Proxy)

Contoh implementasi ringkas untuk panel LLM.

1) Client: hook useLLM (src/hooks/useLLM.ts)
```ts
import { useState } from "react";
import axios from "axios";

export function useLLM() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function queryLLM(prompt: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/llm/chat`, {
        prompt,
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

2) Component ChatPanel (src/components/LLMChatPanel.tsx)
```tsx
import React, { useState } from "react";
import { useLLM } from "../hooks/useLLM";

export function LLMChatPanel() {
  const [prompt, setPrompt] = useState("");
  const [history, setHistory] = useState<Array<{prompt:string, response:string}>>([]);
  const { queryLLM, loading } = useLLM();

  async function send() {
    if (!prompt) return;
    try {
      const data = await queryLLM(prompt);
      setHistory(prev => [{prompt, response: data.text}, ...prev]);
      setPrompt("");
    } catch (e) {
      // error handled in hook
    }
  }

  return (
    <div className="p-4 border rounded-md">
      <textarea
        className="w-full border p-2 rounded"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Tanya sesuatu ke model..."
      />
      <button className="mt-2 btn-primary" onClick={send} disabled={loading}>
        {loading ? "Mengirim..." : "Kirim"}
      </button>

      <div className="mt-4 space-y-3">
        {history.map((h, i) => (
          <div key={i} className="p-3 border rounded">
            <div className="text-sm font-medium">Prompt</div>
            <div className="text-sm">{h.prompt}</div>
            <div className="mt-2 text-sm font-medium">Response</div>
            <div className="text-sm">{h.response}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

3) Minimal Server Proxy (Express) contoh: server/routes/llm.js
```js
const express = require("express");
const router = express.Router();
const axios = require("axios");

router.post("/chat", async (req, res) => {
  const { prompt } = req.body;
  if (!prompt) return res.status(400).json({ message: "Prompt required" });

  try {
    // Contoh: proxy ke OpenAI
    const apiKey = process.env.OPENAI_API_KEY;
    const openAIRes = await axios.post(
      "https://api.openai.com/v1/chat/completions",
      {
        model: "gpt-4o-mini", // sesuaikan
        messages: [{ role: "user", content: prompt }],
        max_tokens: 800,
      },
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
      }
    );

    const text = openAIRes.data?.choices?.[0]?.message?.content || "";
    // Simpan log prompt / response jika perlu
    res.json({ text });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "LLM provider error", detail: err.message });
  }
});

module.exports = router;
```

Catatan keamanan:
- Jangan menaruh kunci API LLM di client. Selalu gunakan backend/proxy untuk memanggil provider LLM.
- Implementasikan rate-limiting, caching, dan quota jika diperlukan.

---

## API Dokumentasi (Contoh Endpoints)

Base URL: {VITE_API_BASE_URL} (contoh: https://api.example.com/api)

1. Auth
- POST /auth/signup
  - Body: { name, email, password }
  - Response: { user, token }

- POST /auth/login
  - Body: { email, password }
  - Response: { user, token }

- POST /auth/refresh
  - Body: { refreshToken }
  - Response: { token }

2. Students
- GET /students
  - Query params: page, limit, q (search), sort
  - Response: { data: [...], meta: { total, page, limit } }

- GET /students/:id
  - Response: { data: { ...student } }

- POST /students
  - Body: { name, email, ... }
  - Response: { data: createdStudent }

- PUT /students/:id
  - Body: { ...fields }
  - Response: { data: updatedStudent }

- DELETE /students/:id
  - Response: { message: "deleted" }

3. LLM (Proxy)
- POST /llm/chat
  - Body: { prompt: string, options?: { model?: string, max_tokens?: number } }
  - Response: { text: string, meta?: { tokens_used } }

- POST /llm/summarize
  - Body: { text: string }
  - Response: { summary: string }

4. Logs (optional)
- GET /llm/logs
  - Response: { data: [ { prompt, response, createdAt } ] }

Format error:
- For error responses, gunakan format:
  ```
  { "message": "Error description", "code": "ERR_CODE", "details": {...} }
  ```

Autentikasi:
- Gunakan header Authorization: Bearer <token> pada request yang dilindungi.

---

## Best Practices & Tips

- Environment:
  - Simpan kunci sensitif di environment variables pada server / deployment.
- Rate limiting:
  - Terapkan rate limiting pada endpoint LLM untuk mencegah biaya tak terduga.
- Logging & Observability:
  - Simpan logs prompt/respons (mask data sensitif) untuk debugging & audit.
- Cost control:
  - Batasi max_tokens pada panggilan LLM dan gunakan model yang sesuai budget.
- Security:
  - Validasi input (Zod) pada server.
  - Gunakan HTTPS, sanitize logs.

---

## Troubleshooting

1. Dev server tidak jalan (npm run dev gagal)
   - Pastikan Node versi kompatibel (Node 16+ direkomendasikan).
   - Hapus node_modules & reinstall:
     ```
     rm -rf node_modules package-lock.json
     npm install
     ```
   - Periksa console errors pada terminal; biasanya ada detail dependency/ESLint error.

2. Environment variables tidak terbaca
   - Vite memerlukan prefix VITE_ untuk variabel yang di-inject ke client (mis: VITE_API_BASE_URL).
   - Jalankan ulang dev server setelah mengubah .env.

3. CORS error ketika client panggil backend
   - Pastikan backend mengizinkan origin dev (http://localhost:5173) atau gunakan proxy di vite.config:
     ```js
     // vite.config.ts
     server: {
       proxy: {
         '/api': 'http://localhost:4000'
       }
     }
     ```

4. 401 Unauthorized
   - Pastikan token tersimpan & dikirim di header Authorization.
   - Periksa expiry token dan mekanisme refresh.

5. LLM response error (500 / provider error)
   - Cek kunci API benar dan belum expired.
   - Periksa rate-limit atau quota di provider LLM.
   - Periksa payload size / max_tokens setting.

6. Build gagal di CI/CD
   - Tambahkan environment variables di CI.
   - Pastikan mesin build menggunakan Node versi yang sesuai.
   - Cek lint/format scripts yang dijalankan sebelum build (bisa disable sementara di pipeline).

---

## Checklist sebelum Produksi

- [ ] Hidden keys: Pastikan tidak ada API key di repo.
- [ ] Rate limits & quotas diterapkan.
- [ ] Logging & monitoring aktif.
- [ ] Backup DB & rollback plan.
- [ ] Test end-to-end integrasi LLM.
- [ ] Implementasi validasi & sanitasi user input.

---

## Contributing

Silakan buat issue atau PR ke repo ini. Gunakan husky untuk memastikan linting & format sebelum commit.

---

## Lisensi

Project ini dilisensikan sesuai dengan file LICENSE di repository (jika ada). Periksa lisensi sebelum penggunaan komersial.

---

Jika Anda ingin, saya dapat:
- Meng-generate template file .env.example
- Menambahkan contoh server Express lengkap (package.json, index.js)
- Membuat dokumentasi OpenAPI (swagger) untuk endpoint di atas

Beritahu mana yang ingin Anda tambahkan dan saya akan buatkan filenya.
