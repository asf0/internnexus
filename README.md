# InternNexus

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Production-ready internship aggregator with AI-powered job matching

**Live Demo:** [demo-link] | **Documentation:** [docs/](docs/)

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
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌──────────┐
         │ Redis  │  │  Ollama  │  │  Green-  │
         │(Cache) │  │(Embeddings)│  │ house    │
         └────────┘  └──────────┘  └──────────┘
```

**Tech Stack:**
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic
- **Database**: PostgreSQL 17 + pgvector extension
- **Cache**: Redis (rate limiting, embedding cache)
- **AI**: Ollama or LM Studio (local embeddings)
- **Geo**: pycountry (ISO country/state lookups)

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Ollama or LM Studio (for embeddings)

### 1. Clone & Setup
```bash
git clone <repository-url>
cd internjobs
cp backend/.env.example backend/.env
# Edit backend/.env with your settings
```

### 2. Start Infrastructure
```bash
docker-compose up -d  # PostgreSQL + Redis
```

### 3. Install & Run Backend
```bash
cd backend
uv pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

> **Note**: pycountry will be installed automatically for location normalization.

### 4. Install & Run Frontend
```bash
cd frontend
bun install
bun run dev
```

### 5. Ingest Jobs
```bash
cd backend
uv run python run_pipeline.py --skip-discover
```

**Done!** Visit http://localhost:3000

---

## 📊 Data Pipeline

The ingestion system runs 4 sequential steps:

| Step | Action | Description |
|------|--------|-------------|
| 1 | **Discover** | Verify companies have active job boards |
| 2 | **Ingest** | Fetch jobs from APIs, deduplicate, enrich |
| 3 | **Cleanup** | Normalize location data (city/state/country) |
| 4 | **Embed** | Generate vector embeddings for matching |

```bash
# Run full pipeline
uv run run_pipeline.py

# Skip discovery (faster, uses cached companies)
uv run run_pipeline.py --skip-discover

# Run continuously every hour
uv run run_pipeline.py --continuous --interval 3600

# Resume interrupted run
uv run run_pipeline.py --resume
```

---

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Complete installation instructions
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Configuration](docs/CONFIGURATION.md)** - Environment variables reference
- **[Pipeline](docs/PIPELINE.md)** - Job ingestion workflow
- **[Backend Docs](docs/backend/)** - API and codebase documentation
- **[Security](docs/SECURITY.md)** - Security policies and best practices
- **[OAuth Setup](docs/OAUTH_SETUP.md)** - GitHub/Google OAuth configuration

---

## 🧪 Testing

```bash
cd backend
pytest                    # Run all tests
pytest --cov=app         # With coverage
pytest -v               # Verbose output
```

---

## 🔧 Configuration

Key environment variables:

```env
# Database
POSTGRES_DB=internjobs
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-super-secret-key

# AI Provider (Ollama recommended)
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for complete reference.

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

We welcome contributions! Please see our [Security Policy](docs/SECURITY.md) for guidelines.

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/your-username/internjobs.git

# 2. Create branch
git checkout -b feature/your-feature

# 3. Make changes and test
pytest

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

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](../../issues)
- 💬 [Discussions](../../discussions)

---

**Built with ❤️ for job seekers everywhere**
