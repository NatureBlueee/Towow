FROM python:3.12-slim

WORKDIR /app

# Install deps — no torch/sentence-transformers needed in production.
# Agent vectors are pre-computed (.npz); demand encoding uses HF Inference API.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir numpy httpx

# Copy backend code
COPY backend/ /app/backend/

# Copy apps (App Store + shared)
COPY apps/ /app/apps/

# Copy pre-computed agent vectors
COPY data/agent_vectors.npz /app/data/agent_vectors.npz

ENV PYTHONPATH=/app/backend:/app

CMD uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8080}
