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

# Copy pyproject.toml and backend code (needed before editable install)
COPY pyproject.toml .
COPY uv.lock .
COPY backend/ ./backend/

# Install Python dependencies using uv (non-dev for production runtime)
# Playwright Python package is installed via project dependencies,
# but browsers are not downloaded in this image.
RUN uv pip install --system --no-cache -e .

# Copy pipeline code
COPY pipeline/ ./pipeline/

# Default command runs pipeline in continuous mode
CMD ["python", "-m", "pipeline.run_pipeline", "-c"]
