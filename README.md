<<<<<<< HEAD
# Combiphar Chatbot Backend - VITA

AI-powered chatbot backend system untuk PT Combiphar menggunakan Flask, LangChain, LangGraph, dan OpenAI GPT dengan arsitektur RAG (Retrieval-Augmented Generation).

## 🚀 Main Features

- **VITA Agent**: Advanced AI agent menggunakan LangGraph untuk workflow orchestration
- **Multi-Document Chat**: Berinteraksi dengan multiple dokumen (PDF, DOC, TXT)
- **Internet Search**: Pencarian real-time dari internet dengan referensi website
- **RAG Architecture**: Retrieval-Augmented Generation dengan PGVector database
- **RESTful API**: Complete API endpoints dengan Swagger documentation
- **JWT Authentication**: Secure authentication dengan access/refresh token
- **Document Management**: Upload, process, dan manage dokumen
- **Real-time Processing**: Background document processing
- **Modular Services**: Microservice architecture dengan clean separation of concerns

## 🛠️ Tech Stack

### Core Framework

- **Python 3.10+**
- **Flask 3.1.1** - Web framework
- **Flask-CORS 6.0.1** - Cross-Origin Resource Sharing
- **Flasgger 0.9.7** - Swagger API documentation

### AI & Machine Learning

- **LangChain 0.3.0** - AI/ML framework
- **LangGraph** - Workflow orchestration untuk AI agents
- **OpenAI API 1.55.3** - Large Language Model (GPT-4o) dan Embeddings

### Database & Storage

- **PostgreSQL** - Relational database
- **PGVector** - Vector similarity search extension untuk PostgreSQL
- **psycopg2-binary 2.9.10** - PostgreSQL adapter
- **SQLAlchemy** - Database ORM dan connection management

### Authentication & Security

- **PyJWT 2.10.1** - JWT token authentication
- **PyCryptodome 3.15.0** - Encryption utilities

### Document Processing

- **PyPDF 5.9.0** - PDF text extraction
- **pdf2image 1.16.3** - PDF to image conversion
- **pdfplumber 0.10.3** - Advanced PDF processing
- **pytesseract 0.3.13** - OCR capabilities
- **Pillow 11.3.0** - Image processing
- **OpenCV 4.6.0** - Computer vision

### Web Scraping & Search

- **DuckDuckGo Search (ddgs) 2.5.2** - Internet search
- **BeautifulSoup4 4.12.2** - HTML parsing
- **requests 2.32.4** - HTTP client

### Development & Deployment

- **Docker** - Containerization
- **python-dotenv 1.1.1** - Environment management

## 🏗️ Architecture Overview

### VITA Agent (LangGraph)

Sistem menggunakan VITA (Virtual Intelligent Text Assistant) agent yang dibangun dengan LangGraph untuk workflow management:

1. **Query Analysis** - Memahami struktur pertanyaan berdasarkan parameter yang diberikan
2. **Document Retrieval** - Mencari dokumen relevan menggunakan vector search
3. **Answer Generation** - Generate jawaban kontekstual dengan retrieved documents
4. **Response Formatting** - Format respons final dengan metadata

### Service Architecture

```
app/
├── agent.py              # Legacy Chatbot class
├── config.py             # Flask app configuration
├── server.py             # Application entry point
├── api/                  # REST API endpoints
├── middlewares/          # Custom middleware
├── services/             # Business logic services
│   ├── agent/           # Agent-related services
│   ├── vita/            # VITA LangGraph agent
│   ├── pull_portal.py   # Portal sync bootstrap
│   └── document_sync_manager.py  # Background sync orchestrator
└── utils/               # Utility functions
```

## 📄 Document Synchronization Flow

Portal documents tetap otomatis disinkronisasi saat container `sync-docs` dijalankan, namun kini tersedia trigger manual berbasis API yang menggunakan `app/services/document_sync_manager.py` agar prosesnya lebih robust dan tidak bergantung pada perintah Docker eksternal.

- **Mulai sinkronisasi**: `POST /documents/sync`Mengembalikan `202 Accepted` ketika job baru berhasil dijadwalkan, atau `409 Conflict` bila masih ada proses yang berjalan. Response menyertakan snapshot status terkini.
- **Cek status**: `GET /documents/sync`Menampilkan status terbaru termasuk `state` (`idle`, `running`, `succeeded`, `failed`), cap waktu mulai/selesai, durasi, pengguna yang memicu, hasil `downloaded_files` dan `ingested_urls`, serta pesan error bila ada.
- **Thread-safe manager**: Semua permintaan melalui API maupun script startup `pull_portal.py` menggunakan `DocumentSyncManager`, sehingga tidak ada overlap pekerjaan dan error tercatat di log backend alih-alih tertahan di container.
- **Persisted state**: Status job disimpan di tabel `document_sync_state`, jadi pemicu dari endpoint maupun cron berbagi lock yang sama untuk mencegah duplikasi proses.
- **Dependensi database**: Manager otomatis menunggu koneksi PostgreSQL sebelum memulai sinkronisasi sehingga aman dijalankan segera setelah deploy atau restart layanan.

### Scheduled Jobs

- **Cron container** menggunakan image dengan dependency yang sama seperti service utama (`Dockerfile.cron` mengikuti `requirements.txt` + deps system).
- Job dijalankan lewat `supercronic`, masing-masing memanggil modul Python (`python3 -m app.services.pull_portal`, dll) sehingga import path konsisten.
- Status sinkronisasi portal tetap dijaga oleh `DocumentSyncManager` + tabel `document_sync_state` untuk mencegah overlap dengan trigger manual.

## 🔐 Authentication System

Sistem autentikasi menggunakan JWT dengan dual-token strategy:

### Token Types

- **Access Token**: JWT, short-lived (15 menit default), untuk akses API
- **Refresh Token**: JWT, long-lived (1 hari default), untuk perpanjangan session
  - Refresh token berisi payload: user_id, type: 'refresh', exp, iat, jti
  - Hanya hash jti yang disimpan di database untuk validasi dan revoke

### Security Features

- Token blacklisting untuk logout
- Automatic token cleanup
- Multi-device logout support
- Configurable token expiration
- Refresh token dapat di-revoke per device (berdasarkan jti)

### Authentication Flow

1. Login → receive access token + refresh token
2. API calls → use access token in Authorization header
3. Token refresh → use refresh token untuk mendapatkan access token baru
4. Logout → revoke refresh token + blacklist access token

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone git@github.com:oemahsolution/backend-llm.git combiphar-be
cd combiphar-be
```

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment file
cp env.example .env

# Edit .env file dengan konfigurasi yang sesuai
nano .env
```

**Required Environment Variables:**

```env
# Portal Combiphar Configuration
PORTAL_KEY_AES=your_aes_key
PORTAL_KEY_BASE64=your_base64_key
PORTAL_KEY_RJ256=your_rj256_key
PORTAL_KEY_IV=your_iv_key

# JWT Configuration
JWT_SECRET_KEY=your_secret_key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=1

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Database Configuration
DB_HOST=localhost
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_DATABASE=combiphar_db

# PGVector Configuration
# Vector search configuration (optional)
VECTOR_DOC_MIN_SCORE=0.3
HYBRID_VECTOR_WEIGHT=0.7

# CORS Configuration (optional)
ALLOWED_ORIGINS=http://localhost:5173,https://vita.combiphar.com

# User Agent (optional)
USER_AGENT=combiphar-chatbot-backend/1.7.2
```

### 4. Database Setup

```bash
# Using Docker (Recommended)
docker-compose -f docker/docker-compose.services.yml up -d

# Or install PostgreSQL manually and run:
psql -U postgres -d combiphar_db -f schema/init.sql
```

### 5. Run Application

```bash
# Development mode
python app/server.py

# Or using Docker (recommended)
docker-compose -f docker/docker-compose.dev.yml up -d
```

Aplikasi akan berjalan di `http://localhost:8070`

## 🐳 Docker Configuration

### Struktur File Docker

```
docker/
├── docker-compose.dev.yml        # Development environment
├── docker-compose.apps.yml       # Production app service
├── docker-compose.services.yml   # Database dan supporting services
├── Dockerfile.dev               # Development image
├── Dockerfile.prod              # Production image
└── README.md                    # Docker documentation
```

### Development Environment

Start development dengan live code reloading:

```bash
# Create network (hanya sekali)
docker network create combiphar-network

# Start all services
docker-compose -f docker/docker-compose.dev.yml up -d

# View logs
docker-compose -f docker/docker-compose.dev.yml logs -f app

# Stop development environment
docker-compose -f docker/docker-compose.dev.yml down
```

### Production Environment

```bash
# Start services (database, etc.)
docker-compose -f docker/docker-compose.services.yml up -d

# Start production app
docker-compose -f docker/docker-compose.apps.yml up -d

# Stop production environment
docker-compose -f docker/docker-compose.apps.yml down
docker-compose -f docker/docker-compose.services.yml down
```

### Key Development Features

- **Live Code Reloading**: Source code mounted as volumes
- **Flask Development Server**: Auto-reload enabled
- **Debug Mode**: Better error messages
- **Separate Volumes**: Development-specific data volumes

### Service URLs

- **Application**: http://localhost:8070
- **API Documentation**: http://localhost:8070/apidocs/
- **PgAdmin**: http://localhost:5050
- **PostgreSQL Database**: http://localhost:5432

## 📚 API Documentation

API documentation tersedia di: `http://localhost:8070/apidocs/`

### Authentication Endpoints

- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (revoke tokens)
- `POST /auth/logout_all` - Logout dari semua device

### Chat Endpoints

- `POST /chats/ask` - Send chat message
- `GET /chats/history` - Get chat history
- `DELETE /chats/{chat_id}` - Delete chat session
- `POST /chats/pin` - Pin/unpin chat
- `POST /chats/rename` - Rename chat session

### Document Endpoints

- `POST /documents` - Upload document
- `GET /documents` - List documents
- `GET /documents/{id}` - Get document detail
- `DELETE /documents/{id}` - Delete document

### Admin Endpoints

- `GET /users` - List users
- `POST /users` - Create user
- `GET /roles` - List roles
- `GET /settings` - Application settings

### Example Chat Request

```bash
curl -X POST http://localhost:8070/chats/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "message": "Apa itu kebijakan remote work?",
    "chat_id": "29f8b1c-4d3e-4f2a-9b1c-4d3e4f2a9b1c"
  }'
```

### Example Response

```json
{
  "data": {
    "answer": "Kebijakan remote work adalah...",
    "confidence": 0.95,
    "source_documents": [
      {
        "content": "Remote work policy...",
        "metadata": {
          "score": 0.98,
          "source": "document",
          "title": "HR_Policy.pdf"
        }
      }
    ],
    "processing_metadata": {
      "processing_time": 2.35,
      "nodes_executed": ["analyze_query", "retrieve_documents", "generate_answer", "format_response"]
    }
  },
  "message": "Berhasil mendapatkan jawaban"
}
```

## 📁 Project Structure

```
combiphar-be/
├── app/                          # Core application package
│   ├── __init__.py
│   ├── agent.py                  # Legacy Chatbot class (deprecated)
│   ├── config.py                 # Flask app & Swagger configuration
│   ├── server.py                 # Application entry point
│   │
│   ├── api/                      # REST API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── chat.py               # Chat endpoints
│   │   ├── documents.py          # Document management endpoints
│   │   ├── user.py               # User management endpoints
│   │   ├── roles.py              # Role management endpoints
│   │   ├── settings.py           # Settings endpoints
│   │   ├── role_settings.py      # Role settings endpoints
│   │   └── specs/                # OpenAPI/Swagger specifications
│   │       ├── auth_login.yml
│   │       ├── chats_ask.yml
│   │       ├── documents_*.yml
│   │       └── ...
│   │
│   ├── middlewares/              # Custom middleware
│   │   ├── __init__.py
│   │   └── cleanup_token.py      # JWT cleanup middleware
│   │
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── pull_portal.py        # Portal integration service
│   │   │
│   │   ├── agent/                # Agent-related services
│   │   │   ├── __init__.py
│   │   │   ├── chat_service.py   # Chat processing service
│   │   │   ├── error_handler.py  # Error handling utilities
│   │   │   ├── message_classifier.py  # Message classification
│   │   │   ├── prompt_service.py      # Prompt management
│   │   │   ├── search_service.py      # Search functionality
│   │   │   └── vectorstore_service.py # Vector database operations
│   │   │
│   │   └── vita/                 # VITA LangGraph agent
│   │       ├── __init__.py
│   │       ├── vita.py           # Main VITA agent class
│   │       ├── state.py          # State management
│   │       └── nodes.py          # Workflow nodes
│   │
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── auth.py               # JWT utilities
│       ├── database.py           # Database connection utilities
│       ├── document.py           # Document processing utilities
│       ├── general.py            # General helper functions
│       ├── portal.py             # Portal API utilities
│       ├── portal_pull.py        # Portal data synchronization
│       ├── vectorstore.py        # PGVector utilities
│       └── README.md             # Utilities documentation
│
├── data/                         # Persistent data storage
│   ├── document/                 # Uploaded documents
│   │   ├── admin/                # Admin uploaded documents
│   │   ├── chats/                # Chat session documents
│   │   └── portal/               # Portal synchronized documents
│   └── db/                       # Local database files (if using SQLite)
│
├── docker/                       # Docker configuration
│   ├── docker-compose.dev.yml    # Development environment
│   ├── docker-compose.apps.yml   # Production app service
│   ├── docker-compose.services.yml # Supporting services
│   ├── Dockerfile.dev            # Development image
│   ├── Dockerfile.prod           # Production image
│   └── README.md                 # Docker documentation
│
├── logs/                         # Application logs
│   └── app.log
│
├── schema/                       # Database schema
│   ├── pgvector.sql              # PGVector schema and extensions
│   ├── init.sql                  # Database initialization script
│   ├── init-latest.sql           # Latest schema version
│   ├── init-old.sql              # Previous schema versions
│   └── migrations.sql            # Database migrations
│
├── secrets/                      # Service account keys
│   └── gothic-imprint-275509-756cbbfe1808.json
│
├── .gitignore                    # Git ignore rules
├── env.example                   # Environment variables template
├── env.example.prod              # Production environment template
├── LICENSE                       # Project license
├── README.md                     # Project documentation
└── requirements.txt              # Python dependencies
```

## 🔧 Configuration

### Environment Variables

| Variable                            | Description                                     | Default                         | Required |
| ----------------------------------- | ----------------------------------------------- | ------------------------------- | -------- |
| `PORTAL_KEY_AES`                  | AES encryption key for portal                   | -                               | ✅       |
| `PORTAL_KEY_BASE64`               | Base64 encoded key for portal                   | -                               | ✅       |
| `PORTAL_KEY_RJ256`                | Rj256 key for portal                            | -                               | ✅       |
| `PORTAL_KEY_IV`                   | Initialization vector for portal                | -                               | ✅       |
| `JWT_SECRET_KEY`                  | JWT secret key                                  | -                               | ✅       |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration                         | 15                              | ❌       |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS`   | Refresh token expiration                        | 1                               | ❌       |
| `OPENAI_API_KEY`                  | OpenAI API key                                  | -                               | ✅       |
| `DB_HOST`                         | Database host                                   | localhost                       | ❌       |
| `DB_USERNAME`                     | Database username                               | postgres                        | ❌       |
| `DB_PASSWORD`                     | Database password                               | -                               | ✅       |
| `DB_DATABASE`                     | Database name                                   | combiphar_db                    | ❌       |
| `VECTOR_DOC_MIN_SCORE`            | Minimum score for vector search results         | 0.3                             | ❌       |
| `HYBRID_VECTOR_WEIGHT`            | Weight for vector vs text search in hybrid mode | 0.7                             | ❌       |
| `ALLOWED_ORIGINS`                 | CORS allowed origins                            | Default list                    | ❌       |
| `USER_AGENT`                      | User agent for web requests                     | combiphar-chatbot-backend/1.7.2 | ❌       |

### Database Schema

Key tables:

- `users` - User accounts dan profile
- `roles` - User roles dan permissions
- `documents` - Uploaded documents metadata
- `chats` - Chat sessions
- `chat_details` - Chat details
- `refresh_tokens` - JWT refresh tokens
- `blacklisted_tokens` - Blacklisted JWT tokens
- `settings` - Application configuration
- `role_settings` - Role-specific settings

## 🔧 Development

### Code Structure Guidelines

- **API Layer**: Handle HTTP requests/responses di folder `api/`
- **Service Layer**: Business logic di folder `services/`
- **Utils Layer**: Utility functions di folder `utils/`
- **VITA Agent**: AI workflow di folder `services/vita/`

### Adding New Features

1. **API Endpoint**: Create di `app/api/`
2. **Business Logic**: Implement di `app/services/`
3. **Database Operations**: Add di `app/utils/database.py`
4. **Documentation**: Update OpenAPI specs di `app/api/specs/`

### Testing

```bash
# Run development server
python app/server.py

# Test API endpoints
curl -X GET http://localhost:8070/health

# Test with Docker
docker-compose -f docker/docker-compose.dev.yml up -d
```

## 🔧 Troubleshooting

### Common Issues

#### Docker Build Issues

```bash
# Rebuild without cache
docker-compose -f docker/docker-compose.dev.yml build --no-cache

# Check logs
docker-compose -f docker/docker-compose.dev.yml logs -f app
```

#### Database Connection Issues

```bash
# Check database status
docker-compose -f docker/docker-compose.services.yml ps

# Test database connection
python -c "from app.utils.database import get_db_connection; print('DB connected:', get_db_connection() is not None)"
```

#### PGVector Issues

```bash
# Check PGVector extension
docker exec combiphar-db psql -U postgres -d combiphar_db -c "SELECT * FROM pg_extension WHERE extname='vector';"

# Test vector operations
python -c "from app.utils.pgvectorstore import PGVectorStore; print('PGVector available:', PGVectorStore.test_connection())"
```

#### Environment Variables

```bash
# Validate environment variables
docker exec combiphar-be env | grep OPENAI_API_KEY

# Check configuration
python -c "import os; print('OpenAI Key:', bool(os.getenv('OPENAI_API_KEY')))"
```

### Reset Environment

```bash
# Stop all containers
docker-compose -f docker/docker-compose.dev.yml down -v
docker-compose -f docker/docker-compose.services.yml down -v

# Remove images
docker rmi $(docker images -q --filter reference="*combiphar*")

# Reset virtual environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📊 Monitoring & Logs

### Application Logs

```bash
# View application logs
tail -f logs/app.log

# Docker logs
docker-compose -f docker/docker-compose.dev.yml logs -f app
```

### Health Check

```bash
# Application health
curl http://localhost:8070/health

# VITA agent status
curl http://localhost:8070/vita/health
```

## 🚀 Deployment

### Production Deployment

1. **Setup Production Environment**:

   ```bash
   cp env.example.prod .env
   # Edit .env dengan production values
   ```
2. **Deploy dengan Docker**:

   ```bash
   docker-compose -f docker/docker-compose.services.yml up -d
   docker-compose -f docker/docker-compose.apps.yml up -d
   ```
3. **Database Migration**:

   ```bash
   docker exec combiphar-db psql -U postgres -d combiphar_db -f /schema/migrations.sql
   ```

### Security Considerations

- Use strong JWT secret keys
- Implement rate limiting
- Use HTTPS in production
- Regular security updates
- Monitor for suspicious activities

## 📝 License

This project is licensed under the terms specified in the LICENSE file.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

Untuk support dan pertanyaan:

- Email: support@combiphar.com
- Website: https://combiphar.com
- Documentation: http://localhost:8070/apidocs/

---

**Version**: 1.7.2
**Last Updated**: September 2024
**Maintained by**: Combiphar IT Team
=======
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
>>>>>>> f0cdf695cce727fc47c62f7ef931e03e6c5adc4f
