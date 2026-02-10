"""
Railway deployment entry point.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import sys
import os
import importlib

# app.py uses relative imports (from .agent_manager, etc.)
# so it must be imported as part of a package, not as a standalone module.
#
# In Railway container: files are in /app/, so this_dir=/app, parent_dir=/
# We must ensure parent_dir is FIRST in sys.path so Python resolves
# "import app" as the /app/ PACKAGE (has __init__.py), not /app/app.py MODULE.
this_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(this_dir)

# Remove this_dir from sys.path to prevent module/package name conflict
while this_dir in sys.path:
    sys.path.remove(this_dir)

# Insert parent_dir at front so the directory is seen as a package
sys.path.insert(0, parent_dir)

# Package name = directory name (e.g. "backend" locally, "app" in Railway)
pkg = os.path.basename(this_dir)
mod = importlib.import_module(f"{pkg}.app")
app = mod.app

__all__ = ["app"]
