# Pipeline Dockerfile (Production)
# This Dockerfile is designed to be built from the project root context
# so it has access to the pipeline project.
#
# NOTE: This is optimized for production pipeline runs (run_pipeline.py).
# Company discovery now uses SearxNG over HTTP.
# Chromium/Playwright browsers are only needed for optional standalone scrapers.
#
# For company discovery, point the pipeline at your local SearxNG instance.
# Standalone scrapers can still be run separately in development:
#   cd pipeline/discovery && python run_discovery.py

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies (lightweight - no browser runtime deps)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pipeline project
COPY pipeline/ ./pipeline/

# Install pipeline project.
# Playwright Python package may still be installed for optional scrapers,
# but browser binaries are not downloaded in this image.
RUN uv pip install --system --no-cache -e ./pipeline

# Default command runs pipeline in continuous mode
CMD ["internnexus-pipeline", "-c"]
