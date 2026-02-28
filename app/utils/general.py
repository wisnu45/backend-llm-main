"""
General utilities for common functionality.
"""

# Global chatbot instance (lazy-loaded)
_chatbot = None

def chatbot():
    """
    Get or create global chatbot instance using lazy loading.
    This prevents circular imports.
    """
    global _chatbot
    if _chatbot is None:
        from app.agent import Chatbot
        _chatbot = Chatbot()
    return _chatbot

def yaml_path(filename):
    """
    Fungsi helper untuk mendapatkan path relatif ke file YAML,
    baik saat dijalankan di Docker maupun lokal.
    """
    import os

    # Cek environment variable yang umum di Docker
    in_docker = os.environ.get("DOCKER_ENV")

    # Path jika di Docker (folder root dicopy ke /app)
    docker_path = os.path.join("/combiphar-be", "app/api/specs", filename)
    if in_docker and os.path.exists(docker_path):
        return docker_path

    # Path lokal - specs ada di app/api/specs/
    local_specs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api", "specs", filename)
    if os.path.exists(local_specs_path):
        return local_specs_path

    # Fallback: path default (tidak ditemukan)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api", "specs", filename)
