#!/bin/bash
cd "$(dirname "$0")/.." 2>/dev/null || cd ..
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
