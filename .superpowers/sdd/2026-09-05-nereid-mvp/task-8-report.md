# Task 8 implementation report: offline Nereid investigation proof

## Delivered

- Added deterministic evidence ZIP construction and `POST /v1/export`; archives have stable member order, timestamps, JSON key ordering, and source-row sorting.
- Added the committed official GDAC replay snapshot (3 source representations / 1,999 levels) and retained both WMO 2902388/cycle 274 sampling representations through normalize, DuckDB joins, metrics, API results, receipt, and export.
- Added explicit multiple-scheme warning and method/assumption disclosure; QC 3/4 remain excluded.
- Replaced the placeholder corpus with 25 diverse bounded cases plus exactly 5 rejection cases. The evaluator invokes configured Azure, compares all expected filters, and enforces a 27/30 threshold; Azure is currently unconfigured, so its live gate is BLOCKED.
- Added browser acceptance startup against the committed snapshot and a loopback-only winning-flow test covering March filters, both identities, profile display, receipt/provenance/QC/methods, ZIP download, member names, and absence of synthetic fallback labels.
- Recorded measured snapshot, latency, browser/rendering, gate ordering, and hygiene limitations in `docs/evidence/acceptance.md`.

## Tests and checks

- `uv run --project pipeline pytest -v` — 37 passed (71 dependency warnings).
- `uv run --project api pytest -v` — 37 passed (71 dependency warnings).
- `pnpm --dir web test` — 18 passed.
- `pnpm --dir web lint` — passed.
- `pnpm --dir web build` — passed.
- `pnpm --dir web exec playwright test` — 2 passed.
- `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts` — 1 passed, run after the ordinary browser suite to restore headed GPU evidence.
- `uv run --project api python docs/evidence/evaluate_queries.py` — expected exit 2: Azure configuration-blocked; no live score measured.
- `git diff --check` — passed.
- `pnpm --dir web licenses list` — completed; installed web licenses enumerated.
- A targeted tracked-file secret-pattern grep found no matches; `gitleaks` and `trufflehog` were unavailable.

## Self-review

The export test checks deterministic bytes despite reversed source rows, exact member order, source checksum, plan, QC summary, method units, and endpoint download disposition. The committed-snapshot store test verifies two representations and QC 3/4 exclusion. Browser request routing aborts and records every non-loopback request. No auth, voice, collaboration, forecast, additional data, or synthetic scientific fallback was added.

## Limitations

Azure credentials are unset; live planner accuracy is configuration-blocked and no 27/30 claim is made. The latency measurement is warm in-process service latency, not an HTTP benchmark. Dedicated secret scanner binaries were absent; repository grep is weaker. Repository evidence supports originality inspection but cannot prove conduct outside the repository.

## Fix round 1

Secured export ownership with bounded plan plus representation IDs, added representation controls and offline coverage, and made the Azure evaluator configuration-aware. Azure remains BLOCKED without configuration.

## Fix round 2

Section cells are now partitioned by `source_profile_index` lanes, preventing cross-representation interpolation. Export timestamps are real UTC generation times, planner refusals are distinct from availability errors, and generated Next instruction files are removed/ignored. The real evaluator exits 2 when Azure is absent; Task 8 remains blocked pending >=27/30 live score.

## Fix round 3 verification

Full exact gate rerun: pipeline 37 passed, API 37 passed, web 18 passed, lint/build passed, ordinary Playwright 2 passed, then headed GPU rendering 1 passed. Evaluator exited 2 configuration-blocked; no live score is claimed.

## Fix round 4 verification

Selected exports now report QC exclusions from parameterized pre-pagination candidate and eligible counts scoped to the selected representations and bounded plan; retained remains the exact server-owned exported row count. The endpoint fixture verifies `retained=3` and `rejected=3` with QC 3/4 absent. Receipt selections reset only when the stable representation identity set changes, covered by a rerender/download test. The winning-flow test parses numeric trajectory bounds and cutoff, inflates the downloaded ZIP with Node built-ins, and proves `selection.csv` contains exactly `1902202/161/0` and `2902388/274/0`, excluding `2902388/274/1`.

Full exact gate rerun: pipeline 38 passed, API 38 passed, web 19 passed, lint/build passed, ordinary Playwright 2 passed, then headed GPU rendering 1 passed. The evaluator again exited 2 configuration-blocked; no live score is claimed.

## Fix round 5 verification

Selected-export QC counters now use only the server-validated, bounded `(wmo, cycle, source_profile_index)` identity set and QC policy; they no longer assert or filter geographic/date fields. This preserves row-limit-independent pre-QC candidate and QC-eligible counts, including QC 3/4 exclusion, for valid `get_profile` export plans. A `/v1/export` regression confirms `get_profile` exports retain 3 and reject 3; the existing `find_profiles` export assertion remains `retained=3` / `rejected=3`.

Full exact gate rerun: pipeline 39 passed (71 warnings), API 39 passed (71 warnings), web 19 passed, lint/build passed, ordinary Playwright 2 passed, then headed GPU rendering 1 passed. GPU evidence was regenerated after ordinary Playwright: 100,000 points measured 57.438 actual R3F FPS with 82.8 ms initialization. The evaluator again exited 2 configuration-blocked; no live score is claimed.
