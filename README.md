# InternNexus

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)](https://www.postgresql.org/)
[![pnpm](https://img.shields.io/badge/pnpm-11.x-orange)](https://pnpm.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Production-ready internship aggregator with AI-powered job matching

**Live Demo:** [jobfinder.asf0.dev](https://jobfinder.asf0.dev)

Try the live app to search internships, apply filters, and test resume-based job matching.

InternNexus aggregates internship opportunities from multiple job boards (Greenhouse, Lever) and provides intelligent filtering, categorization, and AI-powered resume matching.

---

## ✨ Features

- **15,000+ Jobs** from 145+ companies
- **Multi-Source Aggregation**: Greenhouse, Lever, Workday, Ashby, SmartRecruiters
- **Hybrid Search**: Keyword + semantic (vector) search combined for best results
- **Boolean Search**: Advanced syntax (`AND`, `OR`, `NOT`, `"exact"`, `field:value`)
- **AI-Powered Matching**: Resume-to-job matching using local LLM embeddings
- **Smart Categorization**: Automatic job categorization (Software Engineering, Data Science, PM, etc.)
- **Advanced Filtering**: Category, location, visa sponsorship, FAANG+, work mode
- **Pipeline Resume**: Interrupted runs can be resumed from last successful step
- **Production Ready**: Rate limiting, JWT auth, OAuth, comprehensive testing

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Backend   │────▶│  PostgreSQL │
│  (Next.js)  │     │   (FastAPI)  │     │  + pgvector │
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                            ▼
               ┌─────────────────────────────┐
               │        External Services    │
               │  Ollama (embeddings)        │
               │  Greenhouse / Lever / Ashby │
               └─────────────────────────────┘

```

**Tech Stack:**
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic
- **Database**: PostgreSQL 17 + pgvector extension
- **Cache**: In-memory TTL cache (optional external Redis)
- **AI**: Ollama or LM Studio (local embeddings)
- **Geo**: pycountry (ISO country/state lookups)


---

## 🚀 Quick Start

### Prerequisites
- Docker and `docker compose`
- [pnpm](https://pnpm.io/) (frontend package manager)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+
- Ollama or LM Studio (for embeddings)

### 1. Clone & Setup
```bash
git clone <repository-url>
cd internjobs
cp .env.example .env
# Edit .env with your settings
```

### 2. Start Infrastructure
```bash
docker compose up -d db
```

### 3. Install & Run Backend
```bash
cd backend
uv sync --group dev

# Run database migrations
uv run alembic -c alembic.ini upgrade head

# Start the backend server
uv run uvicorn app.main:app --reload
```

> **Note**: pycountry will be installed automatically for location normalization.

### 4. Install & Run Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

### 5. Ingest Jobs
```bash
cd pipeline
uv sync --group dev
uv run internnexus-pipeline --skip-discover
```

**Done!** Visit http://localhost:3000

---

## 📊 Data Pipeline

The ingestion system runs 7 sequential steps:

| Step | Action | Description |
|------|--------|-------------|
| 1 | **Discover** | Verify companies have active job boards |
| 2 | **Sync inactive** | Mark existing jobs inactive before refresh |
| 3 | **Ingest** | Fetch jobs from APIs, deduplicate, and upsert |
| 4 | **Delete inactive** | Remove jobs no longer present upstream |
| 5 | **Cleanup** | Normalize location data (city/state/country) |
| 6 | **Classify** | Categorize jobs with the configured model |
| 7 | **Embed** | Generate vector embeddings for matching |

```bash
# Run from pipeline/
cd pipeline
uv run internnexus-pipeline

# Skip discovery (faster, uses cached companies)
uv run internnexus-pipeline --skip-discover

# Run continuously (interval from config)
uv run internnexus-pipeline -c

# Run with custom interval
uv run internnexus-pipeline -c --interval 3600

# Single step execution
uv run internnexus-pipeline --step discover
uv run internnexus-pipeline --step ingest
uv run internnexus-pipeline --step cleanup
uv run internnexus-pipeline --step embed

# Utility commands
uv run internnexus-pipeline --dry-run    # Preview without changes
uv run internnexus-pipeline --resume     # Resume failed run
uv run internnexus-pipeline --check      # Health checks only
uv run internnexus-pipeline --fresh      # Clear incomplete runs

# Re-process ALL locations (careful!)
uv run internnexus-pipeline --step cleanup --all
```

---

## 📚 Documentation

Documentation is still lightweight. For now, use `README.md`, `backend/.env.example`, and the code in `backend/`, `frontend/`, and `pipeline/` as the primary reference.

---

## 🧪 Testing

```bash
# Backend
cd backend && uv run pytest tests
cd backend && uv run pytest tests --cov=app

# Pipeline
cd pipeline && uv run pytest tests

# Frontend
cd frontend && pnpm run lint && pnpm test
```

---

## 🔧 Configuration

Key environment variables:

```env
# Database
POSTGRES_DB=internnexus
POSTGRES_USER=internnexus
POSTGRES_PASSWORD=secure_password

# Redis (optional; leave empty for in-memory cache)
REDIS_URL=

# Auth (min 32 characters)
AUTH_SECRET=your-super-secret-key-min-32-chars

# AI Provider (Ollama recommended)
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
```

See `.env.example` for additional configuration options.

---

## 🔍 Search Syntax

InternNexus supports advanced boolean search syntax:

| Query | Result |
|-------|--------|
| `python` | Hybrid search (keyword + semantic) |
| `python AND remote` | Both terms required |
| `python OR java` | Either term |
| `python NOT senior` | Exclude senior roles |
| `"software engineer"` | Exact phrase match |
| `title:python` | Search only in title |
| `company:google` | Search only in company |

**Example:** `title:python AND remote NOT senior` → Python remote roles, excluding senior positions.

---

## 🤝 Contributing

We welcome contributions! Please follow standard GitHub fork and PR workflow.

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/your-username/internjobs.git

# 2. Create branch
git checkout -b feature/your-feature

# 3. Make changes and run the checks for the surfaces you touched
cd backend && uv run pytest tests
cd pipeline && uv run pytest tests
cd frontend && pnpm run lint && pnpm test

# 4. Commit and push
git commit -m "Add your feature"
git push origin feature/your-feature

# 5. Create Pull Request
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- [SimplifyJobs](https://github.com/SimplifyJobs) for job data sources
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent framework
- [Ollama](https://ollama.com/) for local AI capabilities

---

## 📞 Support

Python services now have independent project roots: `backend/` and `pipeline/`. There is no shared Python package between them; the PostgreSQL schema and backend admin API are the integration contracts.

- 📖 Documentation (coming soon)
- 🐛 [Issue Tracker](../../issues)
- 💬 [Discussions](../../discussions)

---

**Built with ❤️ for job seekers everywhere**
