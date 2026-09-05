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
service.execute(plan); samples = []
for _ in range(20):
    start = perf_counter(); result = service.execute(plan); samples.append((perf_counter() - start) * 1000)
print(len(result.data), len({(r['wmo'], r['cycle'], r['source_profile_index']) for r in result.data}), sorted(samples)[18])
PY
```

the snapshot had **3 source representations**, **1,999 normalized levels**, and the March 2023 bounded research query returned **1,700 QC-eligible levels / 3 source representations**. Its warm in-process p95 was **174.319 ms** (20 samples; maximum 318.281 ms) on `Linux forgebook 7.1.9-arch1-2 x86_64`. This is an in-process service measurement, not an HTTP end-to-end latency claim.

WMO 2902388/cycle 274 contains two source representations. `source_profile_index` and `vertical_sampling_scheme` remain in normalized levels, API data, profile metrics, receipt identity, and the export; no representation is merged or dropped. The API visibly warns that multiple vertical sampling schemes remain separate. Research mode permits only adjusted QC 1; exploratory mode may permit QC 2; QC 3/4 never enter outputs.

## Validation run

Run in this order on 2026-09-05:

```bash
uv run --project pipeline pytest -v                 # 38 passed (71 dependency warnings)
uv run --project api pytest -v                      # 38 passed (71 dependency warnings)
pnpm --dir web test                                 # 7 files / 19 tests passed
pnpm --dir web lint                                 # passed
pnpm --dir web build                                # passed
pnpm --dir web exec playwright test                 # 2 passed
NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts  # 1 passed
uv run --project api python docs/evidence/evaluate_queries.py
# exits 2: planner evaluation BLOCKED: Azure configuration unavailable;
# no live score measured
```

The full Playwright command runs the rendering test and therefore overwrites `rendering.json`; the headed GPU command was deliberately run afterwards to regenerate Task 6 GPU evidence. It used system Chromium 151.0.0.0 on DISPLAY `:0` / Wayland and reported Intel UHD Graphics 620. The regenerated 100,000-point result was 59.537 actual R3F FPS (150.8 ms initialization); see `rendering.json` for browser user agent, renderer, and probe details.

`web/e2e/winning-flow.spec.ts` starts FastAPI against the committed snapshot and Next.js with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`. It blocks every browser request whose host is not loopback, executes the March filters, parses numeric trajectory bounds and cutoff, confirms both WMO/cycle identities, native depth plot, receipt DOI/QC/method/provenance and the multiple-scheme warning, downloads `nereid-evidence.zip`, verifies the five ZIP member names, and inflates `selection.csv` to prove it contains exactly `1902202/161/0` and `2902388/274/0` while excluding `2902388/274/1`. It fails if synthetic or test-only fallback labels are visible. The focused API export test also verifies exact member order, deterministic bytes for reordered input, sorted selected rows, QC/source fields, units, query plan, QC counts, and download disposition.

## Planner corpus

`query-cases.json` contains exactly 30 diverse natural-language questions: 25 bounded allowed-operation/filter cases and exactly 5 unbounded or injection-like rejection cases. `evaluate_queries.py` invokes configured Azure planning, compares every returned operation and expected filter, and exits nonzero below 27/30. Azure endpoint, key, deployment, and API-version variables were unset, so this run exited 2 with `planner evaluation BLOCKED: Azure configuration unavailable; no score measured`. Therefore the **Task 8 planner gate is BLOCKED**, live planner accuracy is unmeasured, and no score such as 27/30 is claimed. No local natural-language parser was added.

## Hygiene and limitations

`git diff --check` passed. `.env` is ignored (`.gitignore:4`); local snapshots other than the explicit committed replay directory are ignored. `gitleaks` and `trufflehog` were not installed, so no dedicated secret scanner was available; this run did not claim a secret-scan pass. `pnpm --dir web licenses list` enumerated the installed web dependency licenses; no third-party source or asset was added. Repository history/diff and project text were inspected for Task 8 originality, but repository evidence cannot prove absence of copying outside the repository.
