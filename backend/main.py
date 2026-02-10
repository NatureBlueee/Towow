"""
Railway deployment entry point.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import sys
import os
import types
import importlib

# app.py uses relative imports (from .agent_manager, etc.)
# In Railway container, all files are in /app/ — Python's '' in sys.path
# causes "import app" to find app.py (module) instead of app/ (package).
# Fix: pre-register the directory as a package in sys.modules.
this_dir = os.path.dirname(os.path.abspath(__file__))
pkg = os.path.basename(this_dir)

if pkg not in sys.modules:
    fake_pkg = types.ModuleType(pkg)
    fake_pkg.__path__ = [this_dir]
    fake_pkg.__package__ = pkg
    init_file = os.path.join(this_dir, "__init__.py")
    if os.path.exists(init_file):
        with open(init_file) as f:
            exec(compile(f.read(), init_file, "exec"), fake_pkg.__dict__)
    sys.modules[pkg] = fake_pkg

mod = importlib.import_module(f"{pkg}.app")
app = mod.app

__all__ = ["app"]
