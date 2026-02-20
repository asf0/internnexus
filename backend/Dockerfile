# Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv pip install --system --no-cache \
    fastapi \
    uvicorn[standard] \
    sqlalchemy \
    asyncpg \
    psycopg2-binary \
    pydantic[email] \
    pydantic-settings \
    pgvector \
    alembic \
    httpx \
    playwright \
    playwright-stealth \
    openai \
    anthropic \
    pypdf \
    python-multipart \
    slowapi \
    redis \
    python-jose[cryptography] \
    argon2-cffi \
    email-validator \
    geostring \
    pycountry \
    pyyaml

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
