# Pipeline Improvement Implementation Plan

Status legend:
- [ ] pending
- [-] in progress
- [x] completed

Last updated: 2026-02-24
Owner: OpenCode (assistant)

## Goal

Improve pipeline correctness, reliability, maintainability, typing safety, and test coverage through small, low-risk PR-sized changes.

## Ground Rules

- Keep PRs focused and small.
- Add regression tests with each behavioral fix.
- Preserve existing runtime behavior unless explicitly changed.
- Do not introduce breaking CLI changes.

---

## PR 1 - Correctness Hotfixes (Quick Wins)

Status: [x] completed
Risk: low
Priority: high

### Scope
- [x] Fix `--check` exit logic in `pipeline/run_pipeline.py` so unhealthy checks return non-zero.
- [x] Wire `--step cleanup --limit` to `step_cleanup(..., limit=args.limit)` in `pipeline/run_pipeline.py`.
- [x] Update embeddings session wiring to honor injected session in `pipeline/embeddings/pipeline.py`.
- [x] Add regression tests for all three fixes.

### Exit Criteria
- [x] Tests prove previous buggy behavior fails and new behavior passes.
- [x] No unrelated behavior changes.

---

## PR 2 - Reliability Pass: ATS Client Lifecycle

Status: [ ] pending
Risk: low-medium
Priority: high

### Scope
- [ ] Add explicit lifecycle (`close()` or context manager) for:
  - `pipeline/apis/greenhouse_client.py`
  - `pipeline/apis/lever_client.py`
  - `pipeline/apis/ashby_client.py`
- [ ] Ensure lifecycle cleanup in orchestration (`pipeline/pipeline.py`) on success and failure.
- [ ] Add tests asserting cleanup always runs.

### Exit Criteria
- [ ] No leaked clients in normal or failure paths.
- [ ] Tests cover exception path cleanup.

---

## PR 3 - Reliability Pass: Structured Error Propagation

Status: [ ] pending
Risk: medium
Priority: medium-high

### Scope
- [ ] Standardize per-source/per-slug error shape in `pipeline/pipeline.py`.
- [ ] Preserve resilient behavior (continue processing despite per-slug failures).
- [ ] Add structured logging fields: `step`, `source`, `slug`, `run_id` (when available).
- [ ] Add tests for:
  - [ ] 404 cooldown behavior
  - [ ] non-404 failure handling
  - [ ] aggregate failure accounting

### Exit Criteria
- [ ] Errors are machine-readable and consistent.
- [ ] Operational logs are easier to correlate/debug.

---

## PR 4 - Typing Tightening + Schema Safety

Status: [ ] pending
Risk: medium
Priority: medium

### Scope
- [ ] Resolve `JobSource` mismatch between schema and scraper emitters.
- [ ] Replace mutable defaults with `Field(default_factory=...)` in `pipeline/schemas.py`.
- [ ] Add regression tests for source compatibility and model defaults.

### Decision (locked)
- [ ] Expand `JobSource` to include scraper sources (recommended default).
- [ ] Alternative: normalize scraper source labels before schema creation (not selected unless requested).

### Exit Criteria
- [ ] Type model matches produced data.
- [ ] No mutable-default pitfalls remain.

---

## PR 5 - Refactor: Split `run_pipeline.py`

Status: [ ] pending
Risk: medium-high
Priority: medium

### Scope
- [ ] Extract CLI argument parsing into dedicated module.
- [ ] Extract orchestration runner/service logic.
- [ ] Extract continuous loop/backoff logic.
- [ ] Keep entrypoint behavior stable.
- [ ] Update/add tests for `--step`, `--check`, `--continuous`.

### Exit Criteria
- [ ] Smaller modules with clear responsibilities.
- [ ] No CLI regressions.

---

## PR 6 - Import Hygiene / Path Setup

Status: [ ] pending
Risk: high
Priority: medium

### Scope
- [ ] Remove import-time `sys.path` mutation from `pipeline/__init__.py`.
- [ ] Move import/path setup to explicit entrypoints/package setup.
- [ ] Update import-chain tests to new expected behavior.
- [ ] Validate `python -m pipeline.run_pipeline --help` still works.

### Exit Criteria
- [ ] No import side effects at package import time.
- [ ] Import-chain tests remain green.

---

## Test Gates Per PR

- [x] Targeted tests for touched behavior
- [x] `cd backend && uv run pytest tests/test_import_chains.py -v`
- [x] Relevant pipeline unit tests (classification/runner)

---

## Progress Log

- 2026-02-24: Initial plan drafted.
- 2026-02-24: PR 1 completed with 3 correctness fixes and regression tests (`test_pipeline_hotfixes.py`), plus verification of pipeline runner and import-chain gates.
