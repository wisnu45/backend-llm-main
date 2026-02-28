from flask import jsonify
from app.config import app

# Import blueprints from api
from app.api.auth import auth_bp
from app.api.chat import chat_bp
from app.api.documents import documents_bp
from app.api.roles import roles_bp
from app.api.role_settings import role_settings_bp
from app.api.settings import settings_bp
from app.api.storage import storage_bp
from app.api.user import user_bp
from app.api.test import test_bp
from app.api.tools import tools_bp

# Import necessary modules
import os
import sys
import logging

# Ensure project root is in Python path for proper module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def configure_logging() -> None:
    """Configure root logging once per interpreter to prevent duplicate output."""
    if getattr(configure_logging, "_configured", False):
        return

    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear handlers added by Flask/werkzeug to avoid duplicate console output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter('(%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(stdout_handler)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | (%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(file_handler)

    # Let werkzeug reuse the root handlers instead of emitting its own copy
    werkzeug_logger = logging.getLogger('werkzeug')
    for handler in werkzeug_logger.handlers[:]:
        werkzeug_logger.removeHandler(handler)
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = True

    logging.getLogger('agent').setLevel(logging.DEBUG)
    logging.getLogger('database').setLevel(logging.INFO)
    logging.getLogger('chat').setLevel(logging.INFO)

    configure_logging._configured = True


configure_logging()

# Import and initialize middleware
try:
    from app.middlewares.cleanup_token import token_cleanup_middleware
    token_cleanup_middleware.init_app(app)
    logging.info("Token cleanup middleware initialized")
except Exception as e:
    logging.error(f"Token cleanup middleware failed to initialize: {e}")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(documents_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(role_settings_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(user_bp)
app.register_blueprint(test_bp)
app.register_blueprint(tools_bp)

# Error handler for 404
@app.errorhandler(404)
def not_found(error: Exception):
    return jsonify({"message": "Endpoint tidak ditemukan"}), 404

# Default route
@app.route("/", methods=["GET"])
def default_route():
    return jsonify({"message": "Chatbot API by Combiphar"}), 200

# Menggunakan guard untuk mencegah double execution
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8070,
        debug=True,
        use_reloader=True,  # Enable untuk development
        threaded=True
    )
