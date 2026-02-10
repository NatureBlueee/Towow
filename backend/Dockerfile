FROM python:3.12-slim

WORKDIR /srv

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code as a package
COPY . /srv/app/

# Start: import as package so relative imports work
CMD ["sh", "-c", "cd /srv && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
