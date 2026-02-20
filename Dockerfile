# ─────────────────────────────────────────────────────────
#  Dockerfile — Page Pilot (Django 6.0.2)
#  Multi-stage build for a lean production image
# ─────────────────────────────────────────────────────────

# ── Stage 1: Build ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a prefix dir (for clean copy)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app

# Runtime system deps (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Static & media dirs (media kept in /media for volume mounting)
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app

USER appuser

# Render injects $PORT at runtime (default 8000 for local)
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
