"""
Railway deployment entry point.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import sys
import os

# Add backend dir to path so app.py's relative imports work
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
for d in (backend_dir, parent_dir):
    if d not in sys.path:
        sys.path.insert(0, d)

from app import app

__all__ = ["app"]
