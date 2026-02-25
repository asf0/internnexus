# Backend Typing Modernization Plan

## Goal
Complete SQLAlchemy 2 typing modernization after `models.py` migration, keep CI green, and gradually tighten Pyright rules without blocking delivery.

## Current Status
- `backend/app/models.py` migrated to `Mapped[...]` + `mapped_column(...)`.
- Backend typecheck currently passes in basic mode.
- One root virtual environment workflow is established (`.venv` at repo root).

---

## PR 1 - Baseline Cleanup (post-migration stabilization)

### Scope
- `backend/app/api/matching.py`
- `backend/app/config.py`
- `backend/app/repositories/base.py`
- `backend/app/services/resume_service.py`

### Tasks
- Replace temporary typing workarounds with typed helper patterns where possible.
- Keep only necessary inline Pyright suppressions and document intent.
- Ensure no behavior changes.

### Acceptance Criteria
- `uv run --active pyright --project backend backend/app` passes.
- `uvx ruff check backend/app` passes.
- No endpoint behavior regressions.

---

## PR 2 - API Mapper Consolidation

### Scope
- `backend/app/api/admin.py`
- `backend/app/api/matching.py`
- `backend/app/api/jobs.py`
- `backend/app/api/users.py`

### Tasks
- Introduce mapper functions from ORM entities to response schemas.
- Centralize enum-to-string conversion (`source`, `job_type`, `work_mode`).
- Remove duplicated inline transformation logic.

### Acceptance Criteria
- Type-safe response construction in all admin/matching/job/user endpoints.
- Targeted endpoint tests pass.
- No schema response drift.

---

## PR 3 - Repository + Service Contract Typing

### Scope
- `backend/app/repositories/base.py`
- `backend/app/repositories/user.py`
- `backend/app/repositories/job.py`
- `backend/app/repositories/account.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/user_service.py`
- `backend/app/services/job_search.py`

### Tasks
- Tighten repository return types (`Model | None`, typed lists/tuples).
- Remove ambiguous `Any/object` paths at service boundaries.
- Use typed SQLAlchemy result access patterns consistently.

### Acceptance Criteria
- No `object` attribute-access type errors in repo/service layers.
- Unit tests pass for touched services/repositories.
- Typecheck remains green.

---

## PR 4 - Pipeline Boundary Hardening

### Scope
- `pipeline/repositories/sqlalchemy_repo.py`
- `pipeline/pipeline.py`
- `pipeline/pipeline_state.py`

### Tasks
- Stabilize exported/imported backend symbols used by pipeline (`JobSource`, `PipelineRun`, `PipelineRunStatus`, etc.).
- Prevent import regressions with explicit import-safety checks.

### Acceptance Criteria
- Pipeline-related unit tests collect and pass.
- No runtime import errors across backend/pipeline boundary.

---

## PR 5 - Type Strictness Ratchet

### Scope
- `backend/pyproject.toml`
- Any files still requiring temporary ignores

### Tasks
- Keep `typeCheckingMode = "basic"` initially.
- Remove temporary inline ignores gradually.
- Increase diagnostic strictness incrementally (one category at a time).

### Suggested Ratchet Order
1. Re-enable `reportGeneralTypeIssues`
2. Re-enable `reportArgumentType`
3. Re-enable `reportAttributeAccessIssue`
4. Evaluate moving to `typeCheckingMode = "standard"` (or selective strict subsets)

### Acceptance Criteria
- CI remains green at each ratchet step.
- No broad suppressions reintroduced.

---

## Environment & Workflow Standardization

- Use one virtual environment only: repo root `.venv`.
- Run commands from repo root with:
  - `uv run --active ...`
- Avoid `uv run --project backend ...` unless intentionally targeting a backend-local environment.
- Keep backend package install command:
  - `uv pip install -e ./backend[dev]`

---

## Validation Checklist (each PR)

- `uvx ruff check backend/ pipeline/`
- `uv run --active pyright --project backend backend/app`
- `uv run --active pytest backend/tests/unit/ -q`
- Run targeted pipeline tests when touching pipeline files:
  - `backend/tests/unit/test_pipeline_client_lifecycle.py`
  - `backend/tests/unit/test_pipeline_error_propagation.py`
  - `backend/tests/unit/test_pipeline_hotfixes.py`
  - `backend/tests/unit/test_pipeline_runner_classify.py`

---

## Risks & Mitigations

### Risk
Type tightening breaks runtime behavior in service/API paths.

### Mitigation
- Keep PRs small and scoped.
- Add/keep targeted tests around touched endpoints.
- Use mappers for explicit conversion boundaries.

### Risk
Pipeline imports regress due to backend model/export changes.

### Mitigation
- Maintain explicit exported symbol list in pipeline repository bridge.
- Run import-safety and targeted pipeline tests on each change.

---

## Definition of Done

- Models, repositories, services, and key APIs are type-consistent with SQLAlchemy 2 style.
- Backend and pipeline tests pass for touched areas.
- Pyright diagnostics are stricter than current baseline with minimal/no temporary ignores.
- CI remains stable and reproducible under root `.venv` + `uv` workflow.
