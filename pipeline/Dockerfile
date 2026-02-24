# Pipeline Dockerfile (Production)
# This Dockerfile is designed to be built from the project root context
# so it has access to both backend and pipeline code
#
# NOTE: This is optimized for production pipeline runs (run_pipeline.py).
# It does NOT include Chromium/Playwright browsers since those are only
# needed for discovery/scraping which is run separately in development.
#
# For discovery with browser automation, run locally in dev:
#   cd pipeline/discovery && python run_discovery.py

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies (lightweight - no browser deps)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml from root
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies using uv (non-dev for production runtime)
# Playwright Python package is installed via project dependencies,
# but browsers are not downloaded in this image.
RUN uv pip install --system --no-cache -e .

# Copy backend code (needed for imports)
COPY backend/app/ ./backend/app/
COPY backend/alembic/ ./backend/alembic/
COPY backend/alembic.ini ./backend/

# Copy pipeline code
COPY pipeline/ ./pipeline/

# Create __init__.py files to make packages importable if missing
RUN touch backend/__init__.py

# Set PYTHONPATH to include both backend and app for imports
ENV PYTHONPATH=/app:/app/backend

# Default command runs pipeline in continuous mode
CMD ["python", "-m", "pipeline.run_pipeline", "-c"]
