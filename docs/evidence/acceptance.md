# Acceptance evidence

## Pinned replay data

The committed `data/snapshots/indian-ocean-2023-03` replay snapshot is 224 KB on this host and contains official delayed-mode ARGO GDAC source files `D1902202_161.nc` and `D2902388_274.nc`. Its citation is Argo (2026), *Argo float data and metadata from Global Data Assembly Centre (Argo GDAC)*, <https://doi.org/10.17882/42182>. Manifest checksums are `7a4cd01ef4fcbcc004a55d68fbf55c7ae6ac65bed5ec057d30e7d22bc976d645` and `53ed503b9128529c4855183b2a7c6a4418f7c13062f2e3945462261afee9c557` respectively.

Measured with:

```bash
uv run --project api python - <<'PY'
from pathlib import Path
from time import perf_counter
import pyarrow.parquet as pq
from nereid_api.models import QueryPlan
from nereid_api.service import InvestigationService
from nereid_api.store import ArgoStore
snapshot = Path('data/snapshots/indian-ocean-2023-03')
print(pq.read_table(snapshot / 'profiles.parquet').num_rows, pq.read_table(snapshot / 'levels.parquet').num_rows)
service = InvestigationService(ArgoStore(snapshot))
plan = QueryPlan(operation='find_profiles', bbox=(60, 0, 80, 20), start_date='2023-03-01', end_date='2023-03-31', parameters=['TEMP', 'PSAL'])
service.run_plan(plan); samples = []
for _ in range(20):
    start = perf_counter(); result = service.run_plan(plan); samples.append((perf_counter() - start) * 1000)
print(len(result.data), len({(r['wmo'], r['cycle'], r['direction'], r['source_profile_index']) for r in result.data}), sorted(samples)[18])
PY
```

the snapshot had **3 source representations**, **1,999 normalized levels**, and the March 2023 bounded research query returned **1,700 QC-eligible levels / 3 source representations**. Its warm in-process p95 was **157.265 ms** (20 samples; maximum 158.536 ms) on `Linux forgebook 7.1.9-arch1-2 x86_64`. This is an in-process service measurement, not an HTTP end-to-end latency claim.

WMO 2902388/cycle 274 contains two source representations. `source_profile_index` and `vertical_sampling_scheme` remain in normalized levels, API data, profile metrics, receipt identity, and the export; no representation is merged or dropped. The API visibly warns that multiple vertical sampling schemes remain separate. Research mode permits only adjusted QC 1; exploratory mode may permit QC 2; QC 3/4 never enter outputs.

## Validation run

Run on 2026-09-05 after R11 complete export-evidence verification:

```bash
uv run --directory pipeline pytest -q  # passed: 7 tests (186 warnings)
uv run --directory api pytest -q  # passed: 94 tests (2 warnings)
uv run --directory api ruff check src/nereid_api/export.py tests/test_export.py  # passed
npm --prefix web test -- --run  # passed: 9 files / 34 tests
npm --prefix web run lint  # passed
npm --prefix web run build  # passed
cd web && npx playwright test --workers=1  # passed: 2 tests / 2 tests
uv run --project api python docs/evidence/evaluate_queries.py
# exits 2: planner evaluation BLOCKED: Azure configuration unavailable; no live score measured
```

The full offline Playwright replay selects exactly `1902202/161/A/0` and `2902388/274/A/0`, renders two separate profile panels and at least one real committed-snapshot metric with its value, units, vertical uncertainty, method, and QC, derives a gap-masked section from those IDs, verifies longitude/latitude/depth/time trajectory metadata, and confirms the same two IDs are posted to the offline evidence export endpoint. Metric API identifiers are rendered only from the canonical `principal_thermocline` and `strongest_salinity_gradient` IDs; human labels are separate. The accessible section alternative retains every coordinate identity field, distinguishes duplicate WMO/cycle representations, reports each null cell's matching time/distance gap (or masked), and calls non-null cells interpolated derived rather than observed. The GPU benchmark was not rerun because the renderer did not change. `rendering.json` records Intel UHD Graphics 620 and an actual 100,000-point R3F result of **59.684 FPS** (110.1 ms initialization); the hardware-mode test requires at least 30 FPS. The default SwiftShader/headless mode requires only completion with a positive measured FPS, so it does not falsify the hardware target.

Tracked-file scanning found no high-confidence API key/private-key patterns. `pnpm --dir web licenses list` completed (955 output lines). `lens_diagnostics mode=all` could not be measured because the executable is unavailable in this environment. `git diff --check` passed.

## Planner corpus

`query-cases.json` contains exactly 30 diverse natural-language questions: 25 bounded allowed-operation/filter cases and exactly 5 unbounded or injection-like rejection cases. `evaluate_queries.py` invokes configured Azure planning, compares every returned operation and expected filter, and exits nonzero below 27/30. Azure endpoint, key, deployment, and API-version variables were unset, so this run exited 2 with `planner evaluation BLOCKED: Azure configuration unavailable; no score measured`. Therefore the **Task 8 planner gate is BLOCKED**, live planner accuracy is unmeasured, and no score such as 27/30 is claimed. No local natural-language parser was added.

## Hygiene and limitations

`git diff --check` passed. `.env` is ignored (`.gitignore:4`); local snapshots other than the explicit committed replay directory are ignored. `gitleaks` and `trufflehog` were not installed, so no dedicated secret scanner was available; this run did not claim a secret-scan pass. `pnpm --dir web licenses list` enumerated the installed web dependency licenses; no third-party source or asset was added. Repository history/diff and project text were inspected for Task 8 originality, but repository evidence cannot prove absence of copying outside the repository.
