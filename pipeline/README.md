# Pipeline

Job ingestion pipeline: fetches postings from ATS job boards, normalizes locations,
classifies them with an LLM, and generates embeddings for matching.

Roughly 10k lines across six top-level packages. The layout below *is* the
architecture — if you can find the right directory, you have found the code.

## Data flow

The pipeline is linear. The canonical order lives in
[`runtime/step_order.py`](runtime/step_order.py) as `PIPELINE_STEPS` and is the
single source of truth for sequencing and for resuming a failed run:

```
ingest ──> delete_inactive ──> cleanup ──> classify ──> embed
```

| Step | What it does | Code |
|---|---|---|
| `ingest` | Fetch postings, record sightings, upsert changed jobs | `stages/ingest/` |
| `delete_inactive` | Retire jobs absent from a complete sync — **guarded** | `runtime/orchestrator/sync_safety.py` |
| `cleanup` | Normalize city / state / country | `stages/cleanup/` |
| `classify` | LLM category classification | `stages/classification/` |
| `embed` | Vector embeddings for job matching | `stages/embeddings/` |

`delete_inactive` is the only destructive step. It refuses to run when a source
failed to fetch completely, when sighting counts drop sharply against the
previous run, or when the seen-to-stale ratio looks implausible. Read
`sync_safety.py` before touching anything in that path.

## Layout

```
pipeline/
├── cli/            argparse + console-script entrypoints
├── runtime/        orchestration: run state, health, locking, step order
│   └── orchestrator/   PipelineRunner, assembled from mixins
├── stages/         the six work stages, in execution order
│   ├── ingest/
│   │   └── sources/    ATS adapters (Greenhouse, Lever, Ashby)
│   ├── cleanup/
│   │   └── location/   location parsing subsystem
│   ├── classification/
│   └── embeddings/
├── repositories/   database access
├── domain/         JobSchema and enums
└── infra/          settings, db, models, paths, retry, logging, lru
```

Machinery used by exactly one stage lives inside it. `sources/` is imported only
by `ingest/`, and `location/` only by `cleanup/`, so they are nested rather than
sitting at top level pretending to be peers.

Dependencies point downward: `cli → runtime → stages → {repositories, domain, infra}`.

## Where do I add …?

| Task | Where |
|---|---|
| A new ATS source | `stages/ingest/sources/` — implement the `JobSourceClient` protocol in `protocols.py`, then register slug lookup in `registry.py` |
| A new company to crawl | The curated roster at `$DISCOVERY_OUTPUT_DIR/discovered_companies.json` (a persistent volume in deployments), or `data/companies.json` for Greenhouse/Lever |
| A new pipeline step | Add to `PIPELINE_STEPS` in `runtime/step_order.py`, add a `step_*` method in `runtime/orchestrator/steps.py`, gate it in `runner.py` with `_should_run` |
| A tunable knob | `pipeline.yaml` plus the matching model in `infra/pipeline_config.py` |
| An environment variable | `infra/settings.py` (pydantic, reads the repo-root `.env`) |
| A new SQL query | `repositories/` — stages should not build their own statements |
| A category alias | `data/category_mapping.json`, not Python |
| A location rule | `stages/cleanup/location/data/location_constants.json` where it is data; `*_parser.py` where it is behavior |

## Two rules worth knowing

**Never resolve a path from `__file__`.** Import it from
[`infra/paths.py`](infra/paths.py) instead. Path expressions like
`Path(__file__).parents[3]` break *silently* when a file moves — no ImportError,
just the wrong file read or written. `infra/paths.py` is the one module allowed
to know its own depth. Tests have the same rule and the same anchor:
`tests/paths.py`.

Note the two data directories are deliberately different:

- `PACKAGE_DATA_DIR` — read-only lookup data shipped in the wheel
- `runtime_data_dir()` — writable output, honours `$DATA_DIR`, resolved per call

**No two modules share a basename.** A tab labelled `parser.py` tells you
nothing when there are three of them, so names say what the module is:
`response_parser.py` vs `location_parser.py`, `batch_updater.py` vs
`batch_embedder.py`, `async_retry.py` vs `db_retry.py`. Please keep it that way.

## Tests

`tests/unit/` mirrors the source tree one-for-one, so the test for
`stages/ingest/upsert.py` is under `tests/unit/stages/ingest/`. `tests/unit/architecture/`
holds the structural guards — import-graph acyclicity, wheel contents, lazy exports.

```bash
uv run pytest tests/unit -q                 # ~1040 tests, a few seconds
uv run pytest tests/integration -q          # needs Postgres
uv run pytest tests/test_import_chains.py   # entrypoint import safety
uv run ruff check . && uv run pyright --project pyproject.toml
```

Golden fixtures live in `tests/fixtures/`. Two are regenerated rather than
hand-edited — **review the diff, do not accept it blindly**, since these are the
guard against accidental import cycles and behavior drift:

```bash
uv run pytest tests/unit/architecture/test_runtime_import_graph.py --generate-import-graph
uv run pytest --generate-location-fixture
```

## Running it

```bash
uv run internnexus-pipeline                 # full run
uv run internnexus-pipeline --check         # health checks only, no mutation
uv run internnexus-pipeline --dry-run       # full path, no writes
uv run internnexus-pipeline --step ingest   # one step
uv run internnexus-pipeline --resume        # resume a failed run
uv run internnexus-pipeline -c              # continuous
```

Adding a subpackage means adding it to `[tool.setuptools] packages` in
`pyproject.toml`. Miss it and the code still works locally but is absent from the
wheel, so it fails only in Docker —
`tests/unit/architecture/test_wheel_packages.py` is the guard.

## Layer boundaries

`repositories/` imports only downward. Sync result types and source constants
live in `domain/sync_result.py`, stable identity in `domain/job_identity.py`,
and canonical board snapshots in `domain/board_snapshot.py`; job-row
preparation and upsert-statement construction live in
`repositories/job_upsert.py`. The ingestion stage imports these, so the
dependency arrow now points one way.
