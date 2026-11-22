# InternNexus

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.159-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue)](https://www.postgresql.org/)
[![pnpm](https://img.shields.io/badge/pnpm-12.x-orange)](https://pnpm.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Production-ready internship aggregator with AI-powered job matching

**Live Demo:** [jobfinder.asf0.dev](https://jobfinder.asf0.dev)

Try the live app to search internships, apply filters, and test resume-based job matching.

InternNexus aggregates internship opportunities from multiple job boards (Greenhouse, Lever, Ashby) and provides intelligent filtering, categorization, visa sponsorship search, and AI-powered resume matching.

---

## ✨ Features

- **15,000+ Jobs** from 145+ companies
- **Multi-Source Aggregation**: Greenhouse, Lever, Ashby
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
               │  OpenAI-compatible embeddings │
               │  Greenhouse / Lever / Ashby │
               └─────────────────────────────┘

```

**Tech Stack:**
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic
- **Database**: PostgreSQL 18 + pgvector extension
- **Cache**: In-memory TTL cache (optional external Redis)
- **AI**: OpenAI-compatible API (embeddings and classification)
- **Geo**: pycountry (ISO country/state lookups)


---

## 🚀 Quick Start

### Prerequisites
- Docker and `docker compose`
- [pnpm](https://pnpm.io/) (frontend package manager)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.14+
- OpenAI-compatible inference API (for embeddings and classification)

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
uv run internnexus-pipeline
```

**Done!** Visit http://localhost:3000

### Local Terminal Workflow

For day-to-day development, run only Postgres in Docker and run the app services in terminals. Set `POSTGRES_HOST=localhost` in the repo root `.env` when using the local Docker database.

```bash
docker compose up -d db
```

Terminal 1:

```bash
cd backend
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd pipeline
uv run internnexus-pipeline
```

Terminal 3:

```bash
cd frontend
pnpm dev
```

### Bootstrap Admin Access

After signing in once with Google, promote your user from the local database. Replace the email value with the Google email you used to sign in.

```bash
docker exec jobs-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "insert into admins (id, user_id, role, granted_by, notes) select gen_random_uuid(), id, '\''super_admin'\'', id, '\''local dev bootstrap'\'' from users where email = '\''you@example.com'\'' on conflict (user_id) do update set role = excluded.role, granted_by = excluded.granted_by, granted_at = now(), notes = excluded.notes;"'
```

---

## 📊 Data Pipeline

The ingestion system runs 5 sequential steps:

| Step | Action | Description |
|------|--------|-------------|
| 1 | **Ingest** | Fetch jobs from APIs, deduplicate, and upsert |
| 2 | **Delete inactive** | Retire jobs absent from a complete sync (guarded) |
| 3 | **Cleanup** | Normalize location data (city/state/country) |
| 4 | **Classify** | Categorize jobs with the configured model |
| 5 | **Embed** | Generate vector embeddings for matching |

Company discovery is retired. The ATS slug roster is now a curated file read from
`$DISCOVERY_OUTPUT_DIR/discovered_companies.json`, and it is the only source of
Ashby slugs — see `pipeline/README.md` for the data flow.

```bash
# Run from pipeline/
cd pipeline
uv run internnexus-pipeline

# Run continuously (interval from config, default 21600s)
uv run internnexus-pipeline -c

# Run with custom interval
uv run internnexus-pipeline -c --interval 3600

# Single step execution
uv run internnexus-pipeline --step ingest
uv run internnexus-pipeline --step cleanup
uv run internnexus-pipeline --step classify
uv run internnexus-pipeline --step embed

# Ingest and retire jobs missing upstream in one pass
uv run internnexus-pipeline --step ingest --delete-inactive

# Utility commands
uv run internnexus-pipeline --dry-run     # Preview without changes
uv run internnexus-pipeline --resume      # Resume failed run
uv run internnexus-pipeline --check       # Health checks only
uv run internnexus-pipeline --skip-check  # Skip health checks
uv run internnexus-pipeline --fresh       # Clear incomplete runs

# Re-process ALL locations (careful!)
uv run internnexus-pipeline --step cleanup --all
```

### When production runs ingest

There is no automated schedule right now. The former Gitea `pipeline.yml`
workflow was removed with the Gitea migration; it will return as a GitHub
Actions `workflow_dispatch` workflow when the production host has a
self-hosted runner. Until then, start production ingestion manually on the
Docker host. Admin `PipelineCommand` rows are claimed by the next run.

Keep the cadence in mind: `pipeline_runs` and job-sighting retention is pruned
inline by the pipeline's own cleanup step. The former weekly retention job
(which pruned only `mcp_invocations`) was also removed and will return with the
GitHub workflows. A dormant pipeline therefore stops that pruning too.

---

## 📚 Documentation

Documentation is still lightweight. For now, use `README.md`, the root `.env.example`, and the code in `backend/`, `frontend/`, and `pipeline/` as the primary reference.

### MCP access for AI agents

InternNexus exposes authenticated job discovery and saved/applied state to MCP-compatible agents. It does not expose profiles, resumes, passwords, admin operations, raw database access, or pipeline controls. `apply_to_job` records InternNexus state and returns the employer URL; it does not submit an external form.

Create a user-scoped `inx_mcp_…` key in **Account Settings → AI agent access**. The full secret is shown once, expires after 90 days by default (maximum 365), and can be revoked immediately.

Local stdio configuration for Codex:

```toml
[mcp_servers.internnexus]
command = "uv"
args = ["--directory", "/absolute/path/to/internjobs/backend", "run", "internnexus-mcp", "--transport", "stdio"]
env = { INTERNNEXUS_MCP_API_KEY = "inx_mcp_REPLACE_ME" }
```

Start Streamable HTTP with `docker compose up -d mcp`; the local endpoint is `http://localhost:8001/mcp`. Remote Codex configuration keeps the key in the process environment:

```toml
[mcp_servers.internnexus]
url = "https://mcp.example.com/mcp"
bearer_token_env_var = "INTERNNEXUS_MCP_API_KEY"
```

For production, set `MCP_PUBLIC_URL` to the externally routed HTTPS origin and route the TLS tunnel/reverse proxy to `mcp:8001`. Non-local HTTP public URLs are rejected. Available tools are `search_jobs`, `get_job`, `list_saved_jobs`, `save_job`, `unsave_job`, `list_applied_jobs`, `apply_to_job`, and `unmark_applied`; result pages are capped at 50.

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

### CI and container images

GitHub Actions (`.github/workflows/ci.yml`) is the primary CI. It runs the
backend, pipeline, core, and frontend suites, browser tests, audits, and
Compose validation. On pushes to `main`, the `Container Images` job also builds
`linux/amd64` images and pushes them to GHCR:

- `ghcr.io/asf0/internnexus/backend`
- `ghcr.io/asf0/internnexus/pipeline`
- `ghcr.io/asf0/internnexus/frontend`

Images are tagged with the commit SHA and `latest`. Pull requests build the
same images without pushing. Set the `NEXT_PUBLIC_BASE_URL` repository variable
to the production URL before the first `main` image publish; it is baked into
the frontend bundle at build time. `BACKEND_URL` and
`NEXT_PUBLIC_ENABLE_CREDENTIAL_AUTH` are optional repository variables.

Deploy, pipeline, and retention automation were removed with the Gitea
workflows. They will return as GitHub Actions workflows once the production
Docker host has a self-hosted runner; until then, production operations are
manual. The removed workflows remain available in git history.

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

# AI Provider
OPENAI_BASE_URL=http://192.168.0.4:8080/v1
EMBEDDING_MODEL=qwen3-embedding-4b
```

`OPENAI_BASE_URL` must include `/v1`; the client appends the OpenAI endpoint name (for example, `embeddings`) exactly once.

CPU, memory, PostgreSQL WAL/buffer, and log-retention defaults are documented
in `.env.example`. The shipped memory-conscious production profile uses a 2 GiB
database container cap with `shared_buffers=512MB`, `work_mem=8MB`, and
`maintenance_work_mem=128MB`; `effective_cache_size=2GB` is only a query-planner
estimate, not an allocation. Apply these values to the protected host
`/opt/internjobs/production.env` during the next deployment. Measure database
latency, cache-hit ratio, and `docker stats` before raising them.

The services remain intentionally separate: PgBouncer has negligible steady-state
memory cost and bounds database connections; MCP and Cloudflared retain isolated
health checks and independent restart behavior; migrations and pipeline runs are
one-shot containers rather than persistent memory consumers.
Production database migrations must use expand/contract changes: rollback is
health-gated and sequential, restoring backend, MCP, frontend, then ingress
without running an older Alembic revision against the newer schema.

### Production configuration (`/opt/internjobs/production.env`)

Production secrets and configuration live in a single file on the Docker
host: `/opt/internjobs/production.env` (root-owned, `chmod 0600`, inside a
`chmod 0700` directory). The former deploy workflow read this file and appended
the image tags it computed; that workflow was removed with the Gitea
migration, so production changes are currently applied manually on the Docker
host using this file as the Compose environment. Nothing secret is stored in
GitHub or this repository.

- **Editing configuration**: `sudo $EDITOR /opt/internjobs/production.env`,
  then recreate the affected Compose services on the Docker host. Values follow
  Compose dotenv rules; wrap values containing `#`, spaces, or `$` in single
  quotes. The GitHub deploy workflow will restore automated rollouts later.
- **Required keys** (the stack fails without them): `POSTGRES_DB`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`, `AUTH_SECRET`,
  `CLOUDFLARED_TOKEN`, `MCP_PUBLIC_URL`, `NEXT_PUBLIC_BASE_URL`, and
  `RESUME_ENCRYPTION_KEY`. The full key inventory is `.env.example`.
- **`PIPELINE_MAINTENANCE_MODE=true`** stops the pipeline during a rollout
  (formerly a CI variable).
- **Resume encryption**: generate `RESUME_ENCRYPTION_KEY` with the command in
  `.env.example`. Back up PostgreSQL, run `internnexus-rotate-resumes` as a dry
  run, then repeat with `--apply`. Verify dedicated-key decryption before a
  later release removes the temporary legacy-read fallback.
- **`/opt/internjobs/deployed-tags.env`** was maintained by the former deploy
  workflow: it records the image tags currently in production and drives change
  detection and rollback. It is no longer updated while deployment is manual;
  keep it if you want the future GitHub deploy to detect changes and preserve
  rollback tags. If it is deleted, the next automated deploy rebuilds
  everything and cannot roll back images.

See `.env.example` for additional configuration options.

### Database connection pooling

Postgres connections are pooled at two tiers:

1. **Per-process pool (`DatabaseRuntime`).** Each backend/mcp/pipeline process
   owns an async SQLAlchemy engine (asyncpg) plus a lazily-created sync
   engine, sized by `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` (backend and mcp default
   5/5; pipeline defaults to 2/2, set independently via
   `PIPELINE_DB_POOL_SIZE`/`PIPELINE_DB_MAX_OVERFLOW`). This bounds
   connections held by a single process; it does nothing to cap total
   connections across replicas.
2. **Shared transaction-mode PgBouncer pooler.** In `docker-compose.yml`,
   `backend` and `mcp` connect through the `pgbouncer` service
   (`POOL_MODE=transaction`) instead of directly to `db`. PgBouncer
   multiplexes many client connections onto a shared pool of `DEFAULT_POOL_SIZE`
   (`PGBOUNCER_DEFAULT_POOL_SIZE`, default 10) server connections and closes
   idle server backends after `SERVER_IDLE_TIMEOUT` (300s). This is the tier
   that actually bounds Postgres-side connection/memory usage as the app
   scales, independent of how many backend/mcp processes are running.

**Services that bypass PgBouncer and connect directly to `db`:**

- **`pipeline`** holds a session-level Postgres advisory lock for the
  duration of a run (`pg_advisory_lock`, see
  `pipeline/runtime/sync_lock.py`). Advisory locks are session-scoped and
  transaction-mode pooling can hand a session's underlying server connection
  to a different client between transactions, which is incompatible with
  holding a lock across the whole run.
- **`migrate`** runs Alembic DDL, which also expects a stable, unpooled
  session.
- **Integration tests** connect directly via `TEST_DATABASE_URL`, bypassing
  both `db-env`/PgBouncer wiring used by the compose services.

**`DB_STATEMENT_CACHE_SIZE` fallback.** asyncpg's named prepared statements
don't survive a transaction-mode pooler handing the underlying server
connection to a different client between transactions. The current
`pgbouncer` service sets `MAX_PREPARED_STATEMENTS=200`, which is enough for
PgBouncer (>= 1.21) to track and correctly deallocate prepared statements
across handoffs, so this knob is unset (unused) by default. If a PgBouncer
version or configuration without `max_prepared_statements` support is ever
used, set `DB_STATEMENT_CACHE_SIZE=0` for the affected service to disable
asyncpg's client-side statement cache instead.

**Pooling-related environment variables:**

| Variable | Default | Affects |
|---|---|---|
| `DB_POOL_SIZE` | `5` | `backend`, `mcp`, `migrate` per-process pool size |
| `DB_MAX_OVERFLOW` | `5` | `backend`, `mcp`, `migrate` per-process pool overflow |
| `PIPELINE_DB_POOL_SIZE` | `2` | `pipeline` per-process pool size |
| `PIPELINE_DB_MAX_OVERFLOW` | `2` | `pipeline` per-process pool overflow |
| `DB_STATEMENT_CACHE_SIZE` | unset | Optional PgBouncer-compat fallback; disables asyncpg's prepared-statement cache when set (e.g. to `0`) |
| `PGBOUNCER_DEFAULT_POOL_SIZE` | `10` | Shared PgBouncer server-connection pool size (fronts `backend`/`mcp` only) |
| `PGBOUNCER_MEMORY_LIMIT` | `64m` | `pgbouncer` container memory limit |
| `PGBOUNCER_CPU_LIMIT` | `0.5` | `pgbouncer` container CPU limit |

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
- [llama.cpp](https://github.com/ggml-ai/llama.cpp) for local AI capabilities

---

**Built for job seekers everywhere**
