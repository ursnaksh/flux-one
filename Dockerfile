FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt email-validator>=2.0.0

# Copy backend files (app, alembic, seeds)
COPY backend/ .

ENV PYTHONUNBUFFERED=1

# Migrate DB, seed curriculum, and start Uvicorn
CMD sh -c "alembic upgrade head && python -m seeds.vit_pune && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
