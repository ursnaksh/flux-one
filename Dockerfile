FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt email-validator>=2.0.0

# Copy backend source
COPY backend/ .

# Expose port (Render automatically sets $PORT)
ENV PYTHONUNBUFFERED=1

# Run migrations, seed, and launch Uvicorn
CMD sh -c "alembic upgrade head && python -m seeds.vit_pune && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
