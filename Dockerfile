FROM python:3.12-slim

WORKDIR /app

# Install deps (exclude sentence-transformers to save ~460MB)
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -v sentence-transformers /tmp/requirements.txt > /tmp/req-slim.txt && \
    pip install --no-cache-dir -r /tmp/req-slim.txt && \
    pip install --no-cache-dir numpy

# Copy backend code
COPY backend/ /app/backend/

# Copy apps (App Store + shared)
COPY apps/ /app/apps/

ENV PYTHONPATH=/app/backend:/app

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8080"]
