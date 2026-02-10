"""
Railway deployment entry point.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import sys
import os
import importlib

# app.py uses relative imports (from .agent_manager, etc.)
# so it must be imported as part of a package.
this_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(this_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Package name = directory name (e.g. "backend" locally, or "app" in Railway container)
pkg = os.path.basename(this_dir)
mod = importlib.import_module(f"{pkg}.app")
app = mod.app

__all__ = ["app"]
