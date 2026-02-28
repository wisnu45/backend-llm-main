
# 📦 app/utils Documentation

## 📂 Folder Structure

```text
app/utils/
├── __init__.py          # Entry point yang mengexport semua fungsi
├── auth.py              # Autentikasi JWT, password hashing, permissions
├── database.py          # Koneksi database dan operasi safe DB
├── document.py          # Pemrosesan dokumen, OCR, text extraction
├── general.py           # Utilitas umum (chatbot, yaml paths)
├── portal.py            # Integrasi dengan portal Combiphar
├── portal_pull.py       # Service untuk pulling dokumen dari portal
├── vectorstore.py       # Operasi PGVector store
└── README.md           # Dokumentasi ini
```

## Modul dan Fungsi


### 🔐 Authentication (`auth.py`)

```python
# Decorators
require_auth(f)                    # Dekorator untuk validasi JWT token
require_admin(f)                   # Dekorator untuk validasi admin access

# Password utilities
passwd_hash(password)              # Hash password dengan salt
passwd_check(password, hashed)     # Verifikasi password

# JWT token management
create_jwt_token(user_data)        # Buat access token
validate_jwt_token(token)          # Validasi access token
create_refresh_token(user_id)      # Buat refresh token
validate_refresh_token(token)      # Validasi refresh token
revoke_refresh_token(jti)          # Revoke refresh token spesifik
revoke_all_refresh_tokens(user_id) # Revoke semua refresh token user
blacklist_token(token)             # Blacklist access token
cleanup_expired_tokens()           # Cleanup token expired
```


### 🗃️ Database (`database.py`)

```python
# Connection management
getConnection(timeout=1)           # Buat koneksi DB dengan timeout
Connection                         # Class wrapper untuk kompatibilitas

# Safe operations
safe_db_operation(func, *args)     # Wrapper untuk operasi DB aman
with_db_connection(func)           # Decorator untuk operasi DB
safe_db_query(query, params=None)  # Execute query dengan error handling
```


### 📄 Document Processing (`document.py`)

```python
# File validation
validate_file_content(file)        # Validasi konten file upload

# Text extraction
extract_text_from_pdf(file_path)   # Extract text dari PDF
extract_text_from_image_ocr(file)  # OCR untuk image files
extract_text_from_document(file)   # Extract text dari berbagai format

# Vector processing
process_document_for_vector_storage(file, user_id) # Proses dokumen untuk vector store
```


### 🌐 Portal Integration (`portal.py`)

```python
# Token management
create_portal_token(user_data)     # Buat token untuk portal API
create_user_token(user_data)       # Buat user token
validate_portal_token(token)       # Validasi portal token
```


### 📥 Portal Pull Service (`portal_pull.py`)

```python
# Document pulling
pull_from_portal_logic()           # Logic untuk pull dokumen dari portal
```


### 🔍 Vector Store (`vectorstore.py`)

```python
# PGVector operations
get_vectorstore()                  # Get PGVector store instance
```


### 🛠️ General Utilities (`general.py`)

```python
# AI and configuration
chatbot(message, context)         # AI chatbot interaction
yaml_path(filename)               # Get YAML file path
```


## Cara Penggunaan

### 🔄 Backward Compatibility Import

Semua fungsi masih bisa diimport langsung dari `utils` untuk menjaga kompatibilitas:

```python
# Import langsung dari utils (cara lama masih berfungsi)
from utils import require_auth, safe_db_query, chatbot
from utils import create_jwt_token, passwd_hash, get_vectorstore
from utils import extract_text_from_pdf, process_document_for_vector_storage
```


### 📦 Modular Import (Recommended)

Import fungsi secara spesifik dari modul yang sesuai:

```python
# Authentication functions
from utils.auth import require_auth, create_jwt_token, passwd_hash

# Database operations
from utils.database import safe_db_query, getConnection, with_db_connection

# Document processing
from utils.document import extract_text_from_pdf, validate_file_content

# Vector store operations
from utils.pgvectorstore import get_vectorstore

# Portal integration
from utils.portal import create_portal_token, validate_portal_token

# General utilities
from utils.general import chatbot, yaml_path
```


### 🏷️ Module Import

Import seluruh modul dengan alias:

```python
import utils.auth as auth_utils
import utils.database as db_utils
import utils.document as doc_utils

# Penggunaan
@auth_utils.require_auth
def protected_endpoint():
    pass

conn = db_utils.getConnection()
text = doc_utils.extract_text_from_pdf("file.pdf")
```


## Contoh Penggunaan

### Authentication Example

```python
from utils.auth import require_auth, create_jwt_token, passwd_hash

# Decorator usage
@require_auth
def protected_endpoint(**kwargs):
    user = kwargs.get('user')
    return {"message": f"Hello {user['username']}"}

# Token creation
token = create_jwt_token({"user_id": 1, "username": "admin"})

# Password hashing
hashed_password = passwd_hash("my_password")
```


### Database Example

```python
from utils.database import safe_db_query, with_db_connection

# Safe query execution
result = safe_db_query(
    "SELECT * FROM users WHERE id = %s", 
    (user_id,)
)

# Using decorator
@with_db_connection
def get_user_by_id(user_id, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
```


### Document Processing Example

```python
from utils.document import extract_text_from_pdf, process_document_for_vector_storage

# Extract text from PDF
text = extract_text_from_pdf("/path/to/document.pdf")

# Process for vector storage
result = process_document_for_vector_storage(file_obj, user_id=1)
```


## Migrasi dari Struktur Lama

Jika memiliki kode yang menggunakan struktur lama:

```python
# Kode lama
from utils import some_function

# Tetap berfungsi (backward compatible)
from utils import some_function

# Atau gunakan cara baru (recommended)
from utils.specific_module import some_function
```


**Tidak ada breaking changes** - semua import yang sudah ada akan tetap berfungsi.


## Development Guidelines

1. **Tambah fungsi baru**: Letakkan di modul yang sesuai berdasarkan kategori
2. **Export di `__init__.py`**: Jangan lupa export fungsi baru untuk backward compatibility
3. **Dokumentasi**: Update documentation string di setiap modul
4. **Testing**: Test both modular import dan backward compatibility import

## Error Handling

Semua fungsi database menggunakan safe operation pattern:
- `safe_db_operation()` - Wrapper untuk operasi database
- `safe_db_query()` - Query dengan automatic error handling
- `with_db_connection()` - Decorator dengan connection management

Error handling mengikuti pattern yang konsisten dan terintegrasi dengan logging system aplikasi.
