FROM python:3.11-slim

WORKDIR /app

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "email-validator>=2.0.0"

# Copy backend files and root frontend
COPY backend/ .
COPY index.html ./index.html
COPY assets/ ./assets/

ENV PYTHONUNBUFFERED=1

# Execute migrations, seed curriculum + verified syllabus + legacy class accounts, and launch Uvicorn
CMD sh -c "alembic upgrade head && python -m seeds.vit_pune && python -m seeds.syllabus_topics && python -m seeds.legacy_class_accounts && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
