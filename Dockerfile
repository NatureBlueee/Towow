FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir numpy

# PyTorch CPU-only (needed for sentence-transformers import) + ONNX Runtime (actual inference)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir onnxruntime sentence-transformers

# Copy backend code
COPY backend/ /app/backend/

# Copy apps (App Store + shared)
COPY apps/ /app/apps/

ENV PYTHONPATH=/app/backend:/app
# Force ONNX backend to minimize runtime memory
ENV TOWOW_ENCODER_BACKEND=onnx

CMD uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8080}
