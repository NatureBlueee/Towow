"""
Railway deployment entry point.

This file serves as the entry point for Railway deployment.
It imports the FastAPI app from app.py and re-exports it.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import sys
import os

# Add the parent directory to the Python path so that relative imports work
# This is needed because app.py uses relative imports like "from .agent_manager import ..."
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import the app from the web package
from web.app import app

# Re-export the app for uvicorn
__all__ = ["app"]
