# Backend Test Recovery Plan (for Ralph Loop)

## Iteration 1 Baseline (measured)

- Command run: `uv run pytest` in `backend/`
- Result: `43 failed, 364 passed, 31 errors` (438 collected)
- Primary objective: recover a stable, repeatable backend test run by fixing test harness first, then product regressions.

## What is currently broken

### 1) Test environment / harness instability (highest priority)

1. **Schema drift in test DB**
   - Earliest hard failure: `UndefinedColumnError: column users.notes does not exist`.
   - Impact: breaks auth/e2e setup immediately and contaminates downstream failures.

2. **Async DB session/connection misuse under failure**
   - Repeated `asyncpg InterfaceError: cannot perform operation: another operation is in progress`.
   - Seen across auth/jobs/click-tracking integration suites.

3. **Redis client loop mismatch / stale loop resources**
   - `Future attached to a different loop` and `Event loop is closed` from redis async client.
   - Appears in jobs API and e2e paths that hit cache.

4. **Rate limiter bleeding across tests**
   - `429 Too Many Requests` in auth integration where `409` is expected.
   - Indicates shared limiter state not reset between tests.

5. **CWD-dependent fixture path**
   - `FileNotFoundError: backend/tests/fixtures/locations_sample.txt` while running from `backend/`.
   - Fixture path should be resolved from file location, not process cwd.

6. **Non-isolated dataset assumptions**
   - Jobs integration expects tiny fixtures (`total == 1`) but receives large counts (`55340`).
   - Indicates tests are reading pre-existing data rather than an isolated per-test/per-suite state.

### 2) Product-level regressions (after harness is stable)

1. **Search parser**
   - Parentheses tokenization/parsing failures and property tests for nested parentheses.

2. **Classification parser behavior drift**
   - Fails prefixed/multiline canonical extraction and unmappable text rejection.

3. **Cleanup parser normalization drift**
   - Punctuation normalization mismatch (`"são paulo" != "so paulo"`) and `None` handling mismatch.

4. **Crypto/JWT behavior drift**
   - `get_encryptor` tests failing.
   - JWT decode with wrong secret returns payload instead of `None`.

5. **Location cache graceful-degradation contract broken**
   - Generic redis exceptions escape instead of being swallowed.

6. **Text cleaner behavior drift**
   - Markdown code fences not removed as tests expect.

## Recovery execution plan

### Phase A - Stabilize test harness (must finish first)

1. **Fix migration + schema parity in tests**
   - Ensure alembic upgrade is executed against the actual `TEST_DATABASE_URL` in test startup.
   - Add a guard that validates required columns (ex: `users.notes`) before running suites.

2. **Make DB sessions deterministic per test**
   - Rework fixtures to avoid reusing a broken session state after failures.
   - Ensure rollback/cleanup happens even on exceptions and no concurrent use of one session.

3. **Reset/disable shared infra state in tests**
   - Cache: provide a test-safe redis strategy (mock, fake, or isolated test client) and close/reset per test/session.
   - Rate limiter: disable or reset backend limiter in tests so expected status codes are deterministic.

4. **Fix path handling in fixtures**
   - Replace hardcoded relative file open with `Path(__file__)`-based absolute resolution.

5. **Enforce test data isolation**
   - Seed only required data per test and avoid depending on ambient DB rows.
   - Confirm jobs integration totals and filters are deterministic.

### Phase B - Repair product regressions (targeted)

1. `app/services/search_parser.py` for parentheses handling.
2. classification parser extraction/validation behavior.
3. cleanup parser normalization and `None` semantics.
4. crypto encryptor acquisition + JWT wrong-secret decode contract.
5. `pipeline/location/cache.py` generic error handling.
6. text cleaning code-fence stripping behavior.

### Phase C - Test hygiene and guardrails

1. Register pytest marks (`e2e`, `integration`) in backend pytest config to remove warnings.
2. Add a short "sanity" test target for CI that validates DB migration + cache/limiter reset behavior.
3. Keep a running failure inventory and close clusters one by one.

## Verification sequence (after each phase)

1. `uv run pytest tests/integration/test_auth_api.py -v`
2. `uv run pytest tests/integration/test_jobs_api.py -v`
3. `uv run pytest tests/integration/test_click_tracking.py -v`
4. `uv run pytest tests/unit/test_search_parser.py tests/property/test_search_parser_property.py -v`
5. `uv run pytest tests/unit/test_cleanup_parser.py tests/unit/test_location_cache.py -v`
6. `uv run pytest tests/unit/test_crypto.py tests/unit/test_jwt.py tests/unit/test_text.py -v`
7. Full pass: `uv run pytest`

## Completion criteria

- `uv run pytest` passes in `backend/` with deterministic results.
- No schema drift/setup failures.
- No cross-test loop/session/cache/limiter contamination.
- Remaining warnings are intentional and documented.
