"""
Middleware untuk auto-cleanup token expired melalui request middleware
"""

import logging
import time

class CleanupTokenMiddleware:
    """
    Middleware yang menjalankan cleanup token expired pada setiap request
    dengan throttling untuk menghindari cleanup terlalu sering
    """

    def __init__(self, app=None, cleanup_interval=3600):  # Default 1 jam
        self.app = app
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = 0

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        self.app = app

        # Register middleware untuk cleanup pada setiap request
        @app.before_request
        def cleanup_tokens_middleware():
            current_time = time.time()

            # Cek apakah sudah waktunya cleanup (throttling)
            if current_time - self.last_cleanup >= self.cleanup_interval:
                try:
                    # Import di dalam fungsi untuk menghindari circular import
                    from app.utils.auth import cleanup_expired_tokens
                    cleanup_expired_tokens()
                    self.last_cleanup = current_time
                    logging.info("Token cleanup completed via middleware")
                except Exception as e:
                    logging.error(f"Token cleanup failed via middleware: {e}")
                    # Tetap update last_cleanup untuk menghindari spam error
                    self.last_cleanup = current_time

# Instance yang bisa diimport
token_cleanup_middleware = CleanupTokenMiddleware()
