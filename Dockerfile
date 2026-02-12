FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir numpy

# Install sentence-transformers with CPU-only torch (~200MB instead of ~460MB)
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir sentence-transformers

# Copy backend code
COPY backend/ /app/backend/

# Copy apps (App Store + shared)
COPY apps/ /app/apps/

ENV PYTHONPATH=/app/backend:/app

CMD uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8080}
