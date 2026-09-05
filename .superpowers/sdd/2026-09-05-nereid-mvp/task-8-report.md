# Task 8 implementation report: offline Nereid investigation proof

## Delivered

- Added deterministic evidence ZIP construction and `POST /v1/export`; archives have stable member order, timestamps, JSON key ordering, and source-row sorting.
- Added the committed official GDAC replay snapshot (3 source representations / 1,999 levels) and retained both WMO 2902388/cycle 274 sampling representations through normalize, DuckDB joins, metrics, API results, receipt, and export.
- Added explicit multiple-scheme warning and method/assumption disclosure; QC 3/4 remain excluded.
- Replaced the placeholder corpus with 25 diverse bounded cases plus exactly 5 rejection cases. Azure is unconfigured, so the evaluation honestly reports corpus/validator readiness only.
- Added browser acceptance startup against the committed snapshot and a loopback-only winning-flow test covering March filters, both identities, profile display, receipt/provenance/QC/methods, ZIP download, member names, and absence of synthetic fallback labels.
- Recorded measured snapshot, latency, browser/rendering, gate ordering, and hygiene limitations in `docs/evidence/acceptance.md`.

## Tests and checks

- `uv run --project pipeline pytest -v` — 36 passed (71 dependency warnings).
- `uv run --project api pytest -v` — 36 passed (71 dependency warnings).
- `pnpm --dir web test` — 18 passed.
- `pnpm --dir web lint` — passed.
- `pnpm --dir web build` — passed.
- `pnpm --dir web exec playwright test` — 2 passed.
- `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts` — 1 passed, run after the ordinary browser suite to restore headed GPU evidence.
- `uv run --project api python docs/evidence/evaluate_queries.py` — 30 corpus cases / 25 validator-valid / 5 rejection / planner unmeasured.
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
