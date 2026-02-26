# Technical Debt Cleanup Plan for Ralph

## Summary
- **Total Issues**: 316 code smells
- **Languages**: Python (173), TypeScript/JS (143)
- **Approach**: Batch by rule family, lowest-risk first

---

## Phase 1: Python Duplicate Literals (S1192) — 61 issues
**Impact**: HIGH | **Risk**: LOW | **Files**: 10

| File | Count | Action |
|------|-------|--------|
| `pipeline/location/constants.py` | 37 | More constants to extract |
| `pipeline/location/simple_parser.py` | 8 | Use imported constants |
| `backend/app/api/admin.py` | 4 | Extract repeated strings |
| `backend/app/rate_limiter.py` | 3 | Extract repeated strings |
| `backend/alembic/versions/*.py` | 7 | Low priority (migration files) |

**Pattern**: Extract remaining repeated string literals into module-level constants.

---

## Phase 2: Async Without Await (S7503) — 43 issues
**Impact**: MEDIUM | **Risk**: LOW | **Files**: 10

| File | Count | Action |
|------|-------|--------|
| `backend/tests/unit/test_pipeline_runner_classify.py` | 24 | Convert to sync or add proper await |
| `backend/tests/unit/test_pipeline_hotfixes.py` | 5 | Convert to sync or add proper await |
| `backend/tests/unit/test_match_cache_service.py` | 3 | Convert to sync |
| `backend/app/cache/redis_pool.py` | 2 | Convert to sync or remove async |
| `pipeline/classification.py` | 2 | Add await or convert to sync |

**Pattern**: Either add real async/await or convert functions to synchronous.

---

## Phase 3: TypeScript Readonly Props (S6759) — 43 issues
**Impact**: MEDIUM | **Risk**: VERY LOW | **Files**: 40+

**Pattern**: Add `readonly` to all interface props.

**Top files needing attention**:
- `frontend/components/ui/Card.tsx`
- `frontend/app/admin/AdminDashboardClient.tsx`
- `frontend/app/admin/clicks/ClicksClient.tsx`
- `frontend/app/admin/AdminLayoutClient.tsx`
- + 35 more component files

---

## Phase 4: Cognitive Complexity (S3776) — 34 issues (27 Python + 7 TS)
**Impact**: HIGH | **Risk**: MEDIUM | **Files**: 18

| File | Count | Action |
|------|-------|--------|
| `pipeline/run_pipeline.py` | 3 | Split into smaller functions |
| `pipeline/scrapers/linkedin_guest_scraper.py` | 3 | Split large functions |
| `pipeline/location/simple_parser.py` | 2 | Extract helpers |
| `backend/app/api/matching.py` | 2 | Split complex methods |
| `pipeline/cleanup/metadata.py` | 2 | Extract helpers |
| `pipeline/pipeline.py` | 2 | Refactor |

**Pattern**: Extract private helper functions, reduce cyclomatic complexity.

---

## Phase 5: TypeScript Specific Issues

### S7764 (17 issues) — Nested Conditionals
**Files**: `frontend/lib/hooks/useMatchState.ts`, `frontend/components/toolbar/Toolbar.tsx`
**Action**: Flatten nested conditionals

### S6853 (15 issues) — Property Declarations
**Files**: `frontend/components/admin/CreateJobModal.tsx`, `frontend/components/toolbar/Toolbar.tsx`
**Action**: Fix property declaration order

### S3358 (10 issues) — Merged Branches
**Files**: `frontend/components/toolbar/Toolbar.tsx`, `frontend/components/auth/AuthModal.tsx`
**Action**: Merge duplicate case branches

### S1128 (9 issues) — Unused Imports
**Pattern**: Remove unused `import type` statements across 9 files

### S3863 (7 issues) — Prefer `startsWith`
**Files**: `frontend/app/page.tsx`, `frontend/app/profile/page.tsx`, `frontend/lib/api.ts`
**Action**: Replace `.indexOf() === 0` with `.startsWith()`

### S7781/S7780 (12 issues) — Boolean Expressions
**Files**: `frontend/lib/security/jsonld.ts`, `frontend/components/modals/AboutModal.tsx`
**Action**: Simplify boolean expressions

### S7773 (5 issues) — Trailing Spaces
**Action**: Remove trailing whitespace

### S6772 (4 issues) — React Fragment
**Action**: Fix React.Fragment syntax

### S6819 (2 issues) — Interactive Roles
**Files**: `frontend/components/jobs/JobDetailPanelContainer.tsx`, `frontend/components/ui/LoadingSpinner.tsx`
**Action**: Fix ARIA roles

---

## Phase 6: Python Specific Issues

### S1481 (10 issues) — Unused Import
**Files**: Test files, batch processors
**Action**: Remove unused imports

### S1172 (8 issues) — Unused Parameters
**Files**: `pipeline/embeddings/pipeline.py`, `pipeline/classification.py`, etc.
**Action**: Rename to `_param` or remove

### S5869 (4 issues) — Duplicate Regex
**Files**: `pipeline/location/simple_parser.py`, `pipeline/location/constants.py`
**Action**: Compile once, reuse

### S6353 (5 issues) — `except` Without `raise`
**Files**: `backend/app/api/matching.py`, `backend/app/auth/jwt.py`, `frontend/lib/validation.ts`
**Action**: Add `raise` or proper exception handling

### S2737 (2 issues) — `except` Without Logging
**Files**: `backend/app/services/query_embedding_service.py`
**Action**: Add logging in except blocks

### S5727 (2 issues) — HttpXsrf
**Files**: `backend/tests/unit/test_repositories.py`
**Action**: Mock or fix test setup

---

## Phase 7: Remaining Minor Issues (22 issues)

| Rule | Count | Action |
|------|-------|--------|
| S6903 | 2 | Unused imports in `pipeline/apis/utils.py`, `pipeline/discovery/progress_tracker.py` |
| S1871 | 2 | `if/else` with same result |
| S7508 | 2 | `async` function without `await` |
| S1135 | 1 | Unused `TODO` comment |
| S107 | 1 | Hardcoded password (move to config) |
| S1854 | 1 | Dead store |
| S6478 | 1 | React key |
| S6847 | 1 | `JobCard.tsx` - duplicate click handler |
| S7735 | 1 | Unused interface |
| S7772 | 1 | ESM unused import in `next.config.mjs` |
| S7758 | 1 | Unused type |
| S5780 | 1 | Empty `except` clause |
| S5843 | 1 | Regex complexity |
| S7504 | 1 | `async` without `await` |

---

## Execution Order

1. **Phase 3 (S6759)** — 43 issues, trivial `readonly` adds
2. **Phase 1 (S1192)** — 61 issues, mechanical constant extraction
3. **Phase 2 (S7503)** — 43 issues, convert to sync or add await
4. **Phase 5 (TS small fixes)** — ~80 issues, batch edits
5. **Phase 4 (S3776)** — 34 issues, refactor last (higher risk)
6. **Phase 6 (Python misc)** — ~30 issues
7. **Phase 7** — 22 issues, one-offs

---

## PR Strategy

| PR | Focus | Approx Issues |
|----|-------|---------------|
| PR-1 | S6759 (readonly) | 43 |
| PR-2 | S1192 (constants) | 61 |
| PR-3 | S7503 (async) | 43 |
| PR-4 | TS fixes (S7764, S6853, S3358, etc.) | ~80 |
| PR-5 | S3776 (complexity) | 34 |
| PR-6 | Python misc | ~55 |

---

## Quality Gate Notes

Current blockers:
- `new_coverage = 0.0` (threshold 80) — needs test additions
- `new_security_hotspots_reviewed = 0.0` (threshold 100) — Sonar UI permission/workflow issue

---

## File-by-File Breakdown

### python:S1192 (61 issues)
```
pipeline/location/constants.py         37
pipeline/location/simple_parser.py      8
backend/app/api/admin.py                4
backend/alembic/versions/ae3e98b7e08d_*.py  3
backend/app/rate_limiter.py            3
backend/alembic/versions/f2a9b3d2e11c_*.py  2
backend/alembic/versions/2c9d90bafa94_*.py  1
backend/app/api/jobs.py                 1
```

### python:S7503 (43 issues)
```
backend/tests/unit/test_pipeline_runner_classify.py  24
backend/tests/unit/test_pipeline_hotfixes.py          5
backend/tests/unit/test_match_cache_service.py        3
backend/app/cache/redis_pool.py                       2
backend/tests/unit/api/test_click_tracking.py         2
pipeline/classification.py                            2
backend/app/api/jobs.py                               1
backend/app/services/auth_service.py                  1
+ 3 more
```

### typescript:S6759 (43 issues)
```
frontend/components/ui/Card.tsx                       2
frontend/app/admin/AdminDashboardClient.tsx           2
frontend/app/admin/clicks/ClicksClient.tsx           2
frontend/app/admin/AdminLayoutClient.tsx             1
frontend/app/admin/layout.tsx                        1
frontend/app/admin/pipeline/page.tsx                  1
frontend/app/global-error.tsx                         1
frontend/app/jobs/[id]/page.tsx                      1
+ 32 more files
```

### python:S3776 (27 issues)
```
pipeline/run_pipeline.py                    3
pipeline/scrapers/linkedin_guest_scraper.py  3
backend/app/api/matching.py                  2
backend/app/services/query_embedding_service.py  2
pipeline/cleanup/metadata.py                 2
pipeline/discovery/browser_discovery.py      2
pipeline/location/simple_parser.py           2
pipeline/pipeline.py                         2
+ 9 more files
```

### typescript:S7764 (17 issues)
```
frontend/lib/hooks/useMatchState.ts    6
frontend/components/toolbar/Toolbar.tsx 5
frontend/components/jobs/ApplyNowAuthButton.tsx 2
frontend/components/jobs/JobList.tsx    2
frontend/lib/api.ts                    1
frontend/tests/unit/useMatchState.test.ts 1
```

### typescript:S6853 (15 issues)
```
frontend/components/admin/CreateJobModal.tsx        8
frontend/app/admin/users/[id]/page.tsx              2
frontend/components/settings/ProfessionalSection.tsx 2
frontend/components/toolbar/Toolbar.tsx              2
frontend/components/settings/PersonalSection.tsx     1
```

### python:S1481 (10 issues)
```
backend/tests/unit/api/test_click_tracking.py       3
backend/tests/integration/test_click_tracking.py     2
backend/tests/unit/test_base_repository.py           2
pipeline/cleanup/batch_processor.py                  1
pipeline/embeddings/batch_processor.py               1
pipeline/run_pipeline.py                             1
```

### typescript:S3358 (10 issues)
```
frontend/components/toolbar/Toolbar.tsx            4
frontend/components/auth/AuthModal.tsx              2
frontend/app/admin/pipeline/PipelineRunsClient.tsx   1
frontend/app/admin/users/[id]/page.tsx              1
frontend/components/jobs/JobList.tsx                1
frontend/lib/auth.server.ts                         1
```

### typescript:S1128 (9 issues)
```
frontend/app/actions/auth.ts              1
frontend/app/settings/page.tsx           1
frontend/components/auth/OAuthButtons.tsx 1
frontend/components/jobs/JobList.tsx      1
frontend/components/settings/DangerZone.tsx 1
frontend/components/ui/FormField.tsx      1
frontend/components/ui/IconContainer.tsx   1
frontend/components/ui/Input.tsx           1
+ 1 more
```

### python:S1172 (8 issues)
```
pipeline/embeddings/pipeline.py        2
pipeline/embeddings/retry_handler.py   2
pipeline/classification.py             1
pipeline/consolidate_categories.py     1
pipeline/enrichment.py                 1
pipeline/pipeline_state.py             1
```

### typescript:S3776 (7 issues)
```
frontend/app/actions/jobs.ts           1
frontend/app/actions/match.ts          1
frontend/app/admin/users/[id]/page.tsx 1
frontend/auth.ts                        1
frontend/components/jobs/JobList.tsx    1
frontend/components/toolbar/Toolbar.tsx 1
frontend/lib/auth.server.ts            1
```

### typescript:S3863 (7 issues)
```
frontend/app/page.tsx         3
frontend/app/profile/page.tsx 2
frontend/lib/api.ts           2
```

### typescript:S7781 (6 issues)
```
frontend/app/admin/pipeline/PipelineRunsClient.tsx  2
frontend/app/jobs/[id]/page.tsx                     2
frontend/components/common/PasswordInput.tsx        1
frontend/lib/security/jsonld.ts                    1
```

### typescript:S7780 (6 issues)
```
frontend/lib/security/jsonld.ts              5
frontend/components/common/PasswordInput.tsx  1
```

### typescript:S7773 (5 issues)
```
frontend/app/admin/jobs/page.tsx        1
frontend/app/admin/pipeline/page.tsx    1
frontend/app/admin/users/page.tsx       1
frontend/app/page.tsx                  1
frontend/lib/hooks/useUrlFilters.ts     1
```

### Remaining Rules (1-4 issues each)
- typescript:S6772 (4)
- python:S5869 (4)
- typescript:S6353 (3)
- python:S6353 (2)
- python:S2737 (2)
- python:S5727 (2)
- typescript:S6819 (2)
- typescript:S7761 (2)
- python:S6903 (2)
- python:S1871 (2)
- python:S7508 (2)
- python:S1135 (1)
- python:S107 (1)
- typescript:S1854 (1)
- typescript:S6478 (1)
- typescript:S6479 (1)
- typescript:S6847 (1)
- typescript:S7735 (1)
- javascript:S7772 (1)
- typescript:S7758 (1)
- python:S5780 (1)
- python:S5843 (1)
- python:S7504 (1)
