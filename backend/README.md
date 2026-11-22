# Backend

FastAPI service for InternNexus: job search, resume matching, user accounts, the
admin console and an MCP server.

Roughly 11k lines. The layout below *is* the architecture — if you can find the
right directory, you have found the code.

## Layout

```
backend/app/
├── main.py             FastAPI app: middleware, exception handlers, router wiring
├── mcp_server.py       MCP server entrypoint (separate process)
├── rotate_resumes.py   resume re-encryption CLI
├── models.py           SQLAlchemy ORM; user tables layered on internnexus-core's shared tables
├── api/                HTTP transport — routers only, no business logic
│   ├── auth.py
│   ├── jobs.py
│   ├── matching.py         4 routes; scoring/ranking live in services/matching/
│   ├── users/              one module per concern, assembled in __init__.py
│   └── admin/              same pattern
├── schemas/            request/response contracts + ORM→schema mappers
├── services/           business logic
│   ├── jobs/               search, query parsing, location, recency
│   ├── matching/           scoring, ranking, filters, facets, cache
│   ├── users/              profile, saved jobs, resume, auth, query embedding
│   ├── mcp/                API keys, usage analytics
│   └── errors.py
├── repositories/       database access
├── auth/               security primitives: JWT, OAuth, FastAPI dependencies
├── middleware/         logging, query timing, security headers
└── infra/              settings, engine, cache, HTTP client, rate limiting, paths
    └── cache/              Redis with an in-memory TTL fallback
```

Dependencies point downward:

```
api → services → {repositories, schemas, infra}
```

**Nothing below `api/` may import `app.api`.** The service layer used to reach up
into `app.api.schemas` and `app.api.mappers` because response contracts had no home
outside the transport layer; that is what `schemas/` is for. The rule is enforced by
`TestLayering` in `tests/test_import_chains.py`, parametrized over every lower layer.

`auth/` and `middleware/` sit beside `api/` rather than under it: both are imported
by `main.py` during app construction, and `auth/dependencies.py` is consumed by
routers across every module.

## Where do I add …?

| Task | Where |
|---|---|
| A new endpoint | `api/` — the module matching the resource. Add a new file to `api/users/` or `api/admin/` and include it in that package's `__init__.py` |
| A new request/response model | `schemas/` — never inline in a router; services need to import it too |
| Business logic | `services/`, in the subpackage for its domain. If a router grows past orchestration, the logic belongs here |
| A new SQL query | `repositories/` — services should not build their own statements |
| A tunable knob or secret | `infra/config.py` (pydantic-settings, reads the repo-root `.env`), and document it in `.env.example` |
| A rate limit | `infra/rate_limiter.py` — add to `RATE_LIMITS`, then reference by key in the route decorator |
| A cached value | `infra/cache/` — `get_cache_service()` falls back to in-memory TTL when Redis is unconfigured |
| A schema migration | `alembic/versions/` — `uv run alembic revision --autogenerate -m "..."` |
| A new ORM table shared with the pipeline | `packages/internnexus-core/internnexus_core/models.py`, not here. `app/models.py` is only for backend-owned tables and relationships |
| A test | `tests/unit/` mirrors `app/` — put it in the directory matching the module it covers |

## Three rules worth knowing

**Never resolve a path from `__file__`.** Import it from
[`app/infra/paths.py`](app/infra/paths.py) instead; tests use
[`tests/paths.py`](tests/paths.py). Depth expressions like
`Path(__file__).parents[2]` break *silently* when a file moves — no ImportError,
just the wrong file read. This bit twice during the restructure: `config.py` moving
one directory deeper repointed the `.env` at `backend/.env`, and every setting
silently fell back to its default. Those two modules are the only ones allowed to
know their own depth, and a parametrized test enforces it.

**Every package directory needs an `__init__.py`.** `backend/pyproject.toml` sets
`namespaces = false`, so setuptools' `packages.find` skips any directory without
one. `app/api/` and `app/services/` were both missing theirs and were absent from
the built wheel entirely — a failure that never shows up in a source checkout.
Verify with:

```bash
uv build --wheel --out-dir /tmp/whl && unzip -l /tmp/whl/*.whl | grep -c '\.py$'
```

**Schemas are shared, so they cannot live in `api/`.** Both `services/` and
`mcp_server.py` return the same contracts the HTTP routes do. Put them in
`schemas/`, and put ORM→schema conversion in `schemas/mappers.py`.

## Commands

```bash
uv run uvicorn app.main:app --reload   # dev server on :8000
uv run pytest                          # full suite
uv run pytest tests/unit/services      # one layer
uv run ruff check app tests
uv run pyright app
uv run alembic upgrade head
```

Integration and e2e tests need Postgres on `localhost:5432`; without it they error
at fixture setup rather than failing. Unit tests have no external dependencies.

## Test layout

`tests/unit/` mirrors `app/`, so a test lives in the directory matching the module
it covers (`app/services/matching/scoring.py` →
`tests/unit/services/matching/test_scoring.py`). `tests/integration/`,
`tests/e2e/` and `tests/property/` are grouped by kind instead, since they cross
several modules by nature.

`tests/test_import_chains.py` is the structural guard: it checks the layering rule,
the `__file__` rule, entrypoint imports and circular imports. Run it first after
any move — it fails fast and points at the cause.
