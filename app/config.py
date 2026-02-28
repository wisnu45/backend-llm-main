from flask import Flask, jsonify
from flasgger import Swagger
from flask_cors import CORS
from psycopg2 import OperationalError, InterfaceError
import re
import logging
import os

# Create the Flask app
app = Flask(__name__)

# app.config['JSON_SORT_KEYS'] = False  # Disable sorting of JSON keys
# app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False # Disable pretty printing of JSON responses

# Configure Swagger
app.config["SWAGGER"] = {
    "title": "Dokumentasi API Chatbot Vita Combiphar",
    "ui_params": {
        "footer_include": False,
        "docExpansion": "none"
    },
    "uiversion": 3,
    "openapi": "3.0.4",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "static_url_path": "/flasgger_static",
    # "servers": [
    #     {
    #         "url": "http://localhost:8070/",
    #         "description": "Development Server"
    #     },
    #     {
    #         "url": "https://api-chatbot.oemahsolution.com/",
    #         "description": "Staging Server"
    #     }
    # ],

    "info": {
        "title": "Dokumentasi API Chatbot Vita Combiphar",
        "description": "API untuk berinteraksi dengan chatbot, mengelola dokumen, dan administrasi.",
        "version": "1.7.2",
        "contact": {
            "name": "Combiphar",
            "url": "https://combiphar.com",
            # "email": "support@combiphar.com"
        },
        # "license": {
        #     "name": "Combiphar Internal Use",
        #     "url": "https://combiphar.com/license"
        # },
        "termsOfService": "https://www.combiphar.com/id/kebijakan-privasi",
        # "termsOfService": "https://www.combiphar.com/en/privacy-policy",
    },

    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apidocs/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],

    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Masukkan JWT token di header Authorization sebagai Bearer token"
            }
        }
    },

    "security": [
        {
            "bearerAuth": []
        }
    ]
}

# Initialize Swagger
swagger = Swagger(app)

# Configure CORS
# Allowed origins now configurable via environment variable ALLOWED_ORIGINS
# Format: comma-separated list without spaces, e.g.
# ALLOWED_ORIGINS=http://localhost:5173,https://combiphar-chatbot.oemahsolution.com
_env_allowed = os.getenv("ALLOWED_ORIGINS", "").strip()
if _env_allowed:
    # Split by comma and strip each entry, ignore empties
    ALLOWED_ORIGINS = [o.strip() for o in _env_allowed.split(',') if o.strip()]
else:
    # Fallback defaults when env variable not provided
    ALLOWED_ORIGINS = [
        "https://combiphar-chatbot.oemahsolution.com",
        "https://vita.combiphar.com",
    ]
logging.info(f"CORS ALLOWED_ORIGINS set to: {ALLOWED_ORIGINS}")

def is_allowed_origin(origin: str) -> bool:
    if not origin:
        return False
    if origin in ALLOWED_ORIGINS:
        return True
    # Allow *.vercel.app (robust regex)
    if re.match(r"^https://[\w.-]+\.vercel\.app$", origin):
        return True
    # Allow *.ngrok-free.app (robust regex)
    if re.match(r"^https://[\w.-]+\.ngrok-free\.app$", origin):
        return True
    return False

cors = CORS(
    app,
    supports_credentials=True,
    origins="*",  # Use '*' so allow_origin_func is always called
    allow_origin_func=is_allowed_origin,
)

# Ensure Flask handles OPTIONS globally to avoid 500 on preflight
@app.before_request
def handle_options():
    from flask import request, make_response
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', request.headers.get('Access-Control-Request-Headers', '*'))
        response.headers.add('Access-Control-Allow-Methods', request.headers.get('Access-Control-Request-Method', '*'))
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

# Global Database Error Handlers
@app.errorhandler(OperationalError)
def handle_database_operational_error(e):
    logging.error(f"Database Operational Error: {e}")
    return jsonify({"message": "Database tidak tersedia saat ini"}), 503

@app.errorhandler(InterfaceError)
def handle_database_interface_error(e):
    logging.error(f"Database Interface Error: {e}")
    return jsonify({"message": "Terjadi masalah koneksi database"}), 503

@app.errorhandler(ConnectionError)
def handle_connection_error(e):
    logging.error(f"Connection Error: {e}")
    return jsonify({"message": "Layanan tidak tersedia"}), 503

# Custom Database Error Handler
class DatabaseOfflineError(Exception):
    """Custom exception untuk database offline"""
    pass

@app.errorhandler(DatabaseOfflineError)
def handle_database_offline_error(e):
    logging.error(f"Database Offline Error: {e}")
    return jsonify({"message": "Database sedang offline"}), 503

# Ensure a USER_AGENT is set for LangChain community and ddgs web tools
user_agent = os.getenv("USER_AGENT", "combiphar-chatbot-backend/1.7.2")
os.environ["USER_AGENT"] = user_agent
logging.info(f"USER_AGENT set to {user_agent}")
