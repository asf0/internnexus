# Backend Dockerfile
# Build context must be repository root (see docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy lockfiles and backend code (needed before editable install)
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/

# Install project dependencies (non-dev) from lockfile
RUN uv pip install --system --no-cache -e .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
