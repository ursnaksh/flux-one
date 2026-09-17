FROM python:3.11-slim

WORKDIR /app

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt email-validator>=2.0.0

# Copy backend files and root frontend
COPY backend/ .
COPY index.html ./index.html

ENV PYTHONUNBUFFERED=1

# Execute database migration, seed VIT Pune curriculum, and launch Uvicorn
CMD sh -c "alembic stamp base && alembic upgrade head && python -m seeds.vit_pune && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"