# AGENTS.md

Agent operating guide for InternNexus. This file is optimized for autonomous coding agents and also works for human contributors.

## Purpose

- Define the safest and fastest way to ship changes in this repository.
- Provide verified commands and paths for frontend, backend, pipeline, Docker, and CI.
- Standardize behavior for repository-aware coding agents and contributors.

## Repository Map

- `frontend/`: Next.js 16, React 19, TypeScript, Tailwind CSS v4, pnpm.
- `backend/`: FastAPI, SQLAlchemy 2.0, Alembic, pytest, uv. Layered as
  `api/` (routers only) → `services/` (business logic, grouped by domain) →
  `repositories/` + `schemas/` + `infra/`, with `auth/` and `middleware/`
  alongside. See `backend/README.md` for the layout and a "where do I add X?"
  table; read it before making structural changes.
- `pipeline/`: Job ingestion, cleanup, classification, embeddings. Layered as
  `cli/` → `runtime/` (orchestration) → `stages/` (the five pipeline steps) →
  `repositories/` + `domain/` + `infra/`. See `pipeline/README.md` for the data
  flow and a "where do I add X?" table; read it before making structural changes.
- `.github/workflows/`: GitHub Actions CI and GHCR image publishing (`ci.yml`).
- Root and service `pyproject.toml` files: developer tooling and authoritative service configuration.
- `AGENTS.md`: repository-local operating guidance; agent capabilities are supplied by the execution environment.

## Non-Negotiable Rules

- Never commit secrets or hardcode tokens/credentials.
- Do not edit `.env` values unless explicitly requested.
- Avoid destructive commands (`rm -rf`, force git operations, resets) unless explicitly requested.
- Assume worktree may be dirty; do not revert unrelated user changes.
- Prefer non-mutating investigation first (read/search/inspect) before editing.
- Prefer `rg` and `rg --files` for fast codebase search.
- Keep changes focused and minimal for the requested scope.

## Verified Development Commands

Use the exact working directories below.

### Frontend (`frontend/`)

```bash
pnpm dev
pnpm run build
pnpm run lint
pnpm test
```

### Backend (`backend/`)

```bash
uv run uvicorn app.main:app --reload
uv run pytest
uv run pytest --cov=app
uv run pytest -v
uv run alembic upgrade head
```

### Pipeline (`pipeline/`)

```bash
uv run internnexus-pipeline
uv run internnexus-pipeline -c
uv run internnexus-pipeline --step ingest
uv run internnexus-pipeline --step cleanup
uv run internnexus-pipeline --step classify
uv run internnexus-pipeline --step embed
uv run internnexus-pipeline --check
uv run internnexus-consolidate-categories --dry-run
```

### Docker (repo root)

```bash
docker compose up -d
docker compose up -d --build
docker compose down
```

## Agent Workflow Playbooks

### Bug Fix

1. Reproduce issue or identify failing path.
2. Implement minimal fix at root cause.
3. Run targeted tests first, then broader checks if needed.
4. Summarize behavior change, risks, and follow-ups.

### Feature Work

1. Confirm affected interfaces (API schema, route, types, DB model).
2. Implement backend and frontend contract changes together when coupled.
3. Add or update tests around positive and negative behavior.
4. Call out migration/compatibility implications.

### Refactor

1. Lock behavior with tests before structural edits.
2. Refactor incrementally without API drift unless requested.
3. Re-run impacted tests and static checks.
4. Document what improved (complexity, duplication, readability).

### Docs-Only

- Restrict edits to docs unless code changes are explicitly requested.

## Testing and Quality Gates

- Backend test layout: `backend/tests/{unit,integration,e2e,property}/`
- Pipeline test layout: `pipeline/tests/{unit,integration}/`
- Frontend test layout: `frontend/tests/{unit,e2e}/`.
- `.github/workflows/ci.yml` runs import-chain validation, linting, typing, tests,
  browser checks, audits, and publishes `linux/amd64` images to GHCR on `main`.
- Deployment, pipeline, and retention automation are not in the repo right now;
  they were removed with the Gitea migration and will return as GitHub Actions
  workflows once the production runner is available.

Recommended targeted checks:

```bash
# Backend
cd backend && uv run pytest tests/test_import_chains.py -v

# Pipeline
cd pipeline && uv run pytest tests/test_import_chains.py -v
cd pipeline && uv run internnexus-pipeline --help
cd pipeline && uv run internnexus-consolidate-categories --help

# Frontend
cd frontend && pnpm run lint && pnpm test
```

## Project Reality Notes (Keep Accurate)

- Nothing below `backend/app/api/` may import `app.api`. Response contracts live in
  `backend/app/schemas/` precisely so `services/` and `mcp_server.py` can share them.
  `TestLayering` in `backend/tests/test_import_chains.py` enforces this.
- Never resolve a path from `__file__` in `backend/`; import it from
  `backend/app/infra/paths.py` (tests use `backend/tests/paths.py`). Same rule and
  same reason as the pipeline: depth expressions break silently when a file moves.
- Every package directory under `backend/app/` needs an `__init__.py`.
  `backend/pyproject.toml` sets `namespaces = false`, so setuptools silently omits
  any directory without one from the wheel — it fails only in Docker, never in a
  source checkout.
- `backend/tests/unit/` mirrors `backend/app/`; put a new test in the directory
  matching the module it covers.
- Pipeline repo-local entrypoint is `uv run internnexus-pipeline`.
- The underlying pipeline CLI module is `pipeline/cli/run_pipeline.py`.
- Pipeline source adapters live under `pipeline/stages/ingest/sources/`; browser-heavy scrapers are not implemented.
- Pipeline step order is defined once, in `pipeline/runtime/step_order.py`. Company
  discovery was retired; the ATS slug roster is now a curated file read by
  `stages/ingest/sources/registry.py` from `$DISCOVERY_OUTPUT_DIR`. It is the only
  source of Ashby slugs, so do not remove that loader.
- Never resolve a path from `__file__` in `pipeline/`; import it from
  `pipeline/infra/paths.py` (tests use `pipeline/tests/paths.py`). Depth-based
  path expressions break silently when a file moves.
- No two modules in `pipeline/` share a basename. Keep it that way.
- A new pipeline subpackage must be added to `[tool.setuptools] packages` in
  `pipeline/pyproject.toml`, or it is missing from the wheel and fails only in Docker.
- `pipeline/tests/unit/` mirrors the source tree; put a new test in the directory
  matching the module it covers.
- Prefer `docker compose` commands; `docker-compose` is compatibility-only.


## High-Signal Files
- `frontend/auth.ts`
- `frontend/lib/auth.server.ts`
- `frontend/lib/config.ts`
- `backend/README.md`
- `backend/app/main.py`
- `backend/app/infra/config.py`
- `backend/app/infra/paths.py`
- `backend/app/models.py`
- `backend/app/api/auth.py`
- `backend/app/api/jobs.py`
- `backend/app/schemas/`
- `backend/app/services/matching/`
- `backend/tests/test_import_chains.py`
- `pipeline/README.md`
- `pipeline/cli/run_pipeline.py`
- `pipeline/runtime/step_order.py`
- `pipeline/runtime/orchestrator/runner.py`
- `pipeline/runtime/orchestrator/sync_safety.py`
- `pipeline/infra/paths.py`
- `pipeline/infra/pipeline_config.py`
- `.github/workflows/ci.yml`
- `pipeline/stages/ingest/fetch_all.py`
- `docker-compose.yml`

## CI/CD Awareness

- `.github/workflows/ci.yml` tests Python import safety, entrypoints, typing,
  linting, service suites, and browser tests. On `main` it also builds
  `linux/amd64` backend/pipeline/frontend images and pushes them to GHCR.
- Deployment, pipeline, and retention workflows were removed with the Gitea
  migration. Production operations are manual until the GitHub self-hosted
  runner and replacement workflows are added.
- Admin `PipelineCommand` rows are claimed by the next manual pipeline run.
- Keep secret usage in workflow files via `${{ secrets.* }}` and `${{ vars.* }}` only.

## Environment and Security

Primary runtime configuration is from repo root `.env` and service-specific env loading in code.

- Backend settings: `backend/app/infra/config.py`
- Frontend auth config: `frontend/auth.ts`
- Container orchestration env wiring: `docker-compose.yml`

Minimum security expectations:

- `AUTH_SECRET` must be strong (backend enforces minimum length).
- OAuth provider credentials and resume encryption keys must never be logged or committed.
- Avoid exposing backend tokens to client-side code paths.

### Maintenance & Data Retention

- **`RESUME_ENCRYPTION_KEY` is required in production.** New resume ciphertexts use
  this dedicated Fernet key; without it, resume uploads fail. Legacy blobs encrypted
  with the old `AUTH_SECRET`-derived key still decrypt (MultiFernet). It is independent
  of `AUTH_SECRET` — rotating the JWT secret does not affect resume decryption.
  Rotate the key by generating a new one, then re-encrypting existing rows (dry-run by
  default): `docker compose run --rm backend python -m app.rotate_resumes --apply`.
- **`IP_HASH_SECRET`** (optional) keys the click-analytics IP pseudonym; falls back to
  `AUTH_SECRET` when unset.
- **Analytics retention.** `mcp_invocations` is pruned by
  `docker compose run --rm backend python -m app.prune_analytics --apply` (retention
  window: `MCP_INVOCATION_RETENTION_DAYS`, default 90). The former weekly Gitea
  retention job was removed with the migration and will return as a GitHub
  Actions workflow. `pipeline_runs` and job sightings are pruned inline
  during the pipeline's own cleanup step (see `pipeline/repositories/sightings.py`).
