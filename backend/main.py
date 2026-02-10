"""
Railway deployment entry point.

In Railway container, files are in /app/. The start command is:
    cd .. && uvicorn app.main:app --host 0.0.0.0 --port $PORT

This ensures Python sees /app/ as a package, enabling relative imports.
"""

from .app import app

__all__ = ["app"]
