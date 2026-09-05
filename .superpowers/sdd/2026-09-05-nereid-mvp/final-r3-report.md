# R3 final report

Commit: `7ac7d25 fix: complete the linked scientific workflow`

Implemented workspace-owned exact profile representation selection. The default winning flow selects two deterministic representations; plots, typed metrics/refusals, section derivation, and export all consume that same state. Section requests are abortable and retain prior valid data when a later request fails. Profile panels stay separate by source representation and label raw in-situ/Practical fields separately from adjusted Conservative Temperature/Absolute Salinity fields.

Validation actually run:

- `uv run --project pipeline pytest -v` — 64 passed, 188 warnings.
- `uv run --project api pytest -v` — 64 passed, 188 warnings.
- `pnpm --dir web test --run` — 7 files, 17 tests passed.
- `pnpm --dir web lint` — passed.
- `pnpm --dir web build` — passed.
- `pnpm --dir web exec playwright test` — 2 passed.
- `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts` — 1 passed; 56.340 FPS for 100,000 points on recorded Intel UHD Graphics 620.
- `uv run --project api python docs/evidence/evaluate_queries.py` — expected exit 2, Azure configuration unavailable; no live score measured.
- tracked-file high-confidence secret-pattern scan — no matches.
- `pnpm --dir web licenses list` — completed (955 lines).
- `lens_diagnostics mode=all` — unavailable (`command not found`).
- `git diff --check` — passed.

Residual limitation: Azure evaluator remains blocked/unmeasured; lens diagnostics executable is not installed. No product-scoped issue is known from the implemented workflow tests.


## R3 fix round 1

Section invalidation now aborts and clears on any selection update and on every main-query replacement; stale section promise success, error, and finally paths are guarded by controller identity. Raw profile labels now identify Practical Salinity as PSS-78/unitless.

Validation actually run:

- `pnpm --dir web test --run src/components/InvestigationWorkspace.test.tsx` — 7 passed.
- `uv run --project pipeline pytest pipeline/tests -v` — 7 passed, 186 warnings.
- `uv run --project api pytest api/tests -v` — 57 passed, 2 warnings.
- `pnpm --dir web test --run` — 7 files, 19 tests passed.
- `pnpm --dir web lint` and `pnpm --dir web build` — passed.
- `pnpm --dir web exec playwright test` — 2 passed.
- `uv run --project api python docs/evidence/evaluate_queries.py` — expected exit 2; Azure blocked/unmeasured.
- `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts` — 1 passed, run last; 58.303 FPS at 100,000 points.
