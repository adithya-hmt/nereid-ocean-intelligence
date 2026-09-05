# Nereid MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible ARGO investigation workflow that turns a bounded natural-language or explicit query into real, QC-aware profiles, deterministic thermocline/salinity analytics, linked 4D visualization, and an exportable scientific receipt.

**Architecture:** A uv workspace contains an offline-capable NetCDF-to-Parquet pipeline and a FastAPI service that queries Parquet with DuckDB. A Next.js 16 application renders the result envelope; Azure OpenAI is an optional typed-query planner, never a calculator or SQL generator.

**Tech Stack:** Python 3.12, uv, xarray, netCDF4, argopy, GSW/TEOS-10, PyArrow, DuckDB, FastAPI, Pydantic, OpenAI Python 2.x, pytest, Next.js 16, React 19, TypeScript, React Three Fiber, Three.js, Vitest, Playwright

**Spec:** `docs/superpowers/specs/2026-09-05-nereid-design.md`

## Global Constraints

- Preserve raw and adjusted observations, QC flags, adjusted errors, data mode, WMO, cycle, position, time, source URL, checksum, fetch timestamp, and snapshot DOI.
- QC=3/4 never enters scientific outputs; research mode uses adjusted QC=1; exploratory mode may include QC=2 with a visible label.
- Language models may return only a validated `QueryPlan`; deterministic code performs every numerical operation.
- No authentication, voice input, unrestricted SQL, forecasting, synthetic fallback measurements, or silent stale/live mixing.
- The winning workflow must replay offline after snapshot preparation.
- Every result must contain data, provenance, QC summary, methods, assumptions, and warnings.
- Existing FloatChat repositories are research references only; no code, branding, prompts, layouts, screenshots, or datasets may be copied.

## File Map

```text
floatchat/
├── .env.example                         public configuration names only
├── .gitignore                           generated data, secrets, caches, builds
├── .python-version                      Python 3.12
├── package.json                         root pnpm scripts
├── pnpm-workspace.yaml                  web workspace
├── pyproject.toml                       uv workspace
├── api/
│   ├── pyproject.toml                   API dependencies and pytest config
│   ├── src/nereid_api/
│   │   ├── analytics.py                 thermocline and salinity-gradient calculations
│   │   ├── export.py                    evidence bundle creation
│   │   ├── main.py                      FastAPI application
│   │   ├── models.py                    QueryPlan and ResultEnvelope contracts
│   │   ├── planner.py                   explicit and optional Azure planners
│   │   ├── service.py                   operation dispatch and envelope assembly
│   │   └── store.py                     bounded DuckDB queries
│   └── tests/                           API, analytics, planner, and export tests
├── pipeline/
│   ├── pyproject.toml                   ingestion dependencies and CLI
│   ├── src/nereid_pipeline/
│   │   ├── cli.py                       prepare-snapshot entry point
│   │   ├── manifest.py                  checksums and source manifests
│   │   └── normalize.py                 ARGO NetCDF normalization
│   └── tests/                           generated NetCDF fixture and ingestion tests
├── data/
│   ├── fixtures/                        one small redistributable test fixture
│   └── README.md                        snapshot preparation and data citation
├── web/
│   ├── src/app/                         Next.js page, layout, and global styles
│   ├── src/components/                  workspace, controls, charts, globe, receipt
│   ├── src/lib/                         API client, contracts, geometry, benchmark data
│   ├── src/test/                        Vitest setup and component tests
│   └── e2e/                             Playwright winning-flow test
└── docs/evidence/                       measured benchmark output
```

---

### Task 1: Reproducible repository foundation

**Files:**

- Create: `.gitignore`
- Create: `.python-version`
- Create: `.env.example`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `pyproject.toml`
- Create: `api/pyproject.toml`
- Create: `pipeline/pyproject.toml`
- Create: `api/src/nereid_api/__init__.py`
- Create: `pipeline/src/nereid_pipeline/__init__.py`
- Create via scaffold: `web/`
- Create: `web/vitest.config.ts`
- Create: `web/src/test/setup.ts`
- Test: `web/src/app/page.test.tsx`

**Interfaces:**

- Produces: `uv run --project api pytest`, `uv run --project pipeline pytest`, and `pnpm --dir web test` commands.
- Produces: environment names `NEREID_DATA_DIR`, `NEXT_PUBLIC_API_URL`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, and `OPENAI_API_VERSION`.

- [ ] **Step 1: Create workspace configuration**

Use Python 3.12 and two uv members:

```toml
# pyproject.toml
[tool.uv.workspace]
members = ["api", "pipeline"]
```

```toml
# api/pyproject.toml
[project]
name = "nereid-api"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "duckdb>=1.4,<2",
  "fastapi>=0.116,<1",
  "gsw>=3.6,<4",
  "numpy>=2.2,<3",
  "openai>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "pyarrow>=20,<21",
  "uvicorn[standard]>=0.35,<1",
]

[dependency-groups]
dev = ["httpx>=0.28,<1", "pytest>=8.4,<9", "pytest-asyncio>=1.1,<2"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```toml
# pipeline/pyproject.toml
[project]
name = "nereid-pipeline"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "argopy>=1.3,<2",
  "gsw>=3.6,<4",
  "netcdf4>=1.7,<2",
  "numpy>=2.2,<3",
  "pyarrow>=20,<21",
  "xarray>=2025.6,<2027",
]

[project.scripts]
nereid-prepare = "nereid_pipeline.cli:main"

[dependency-groups]
dev = ["pytest>=8.4,<9"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Scaffold the web app with official Next.js Vitest example**

Run:

```bash
pnpm create next-app@16.2.9 web --example with-vitest --use-pnpm
pnpm --dir web add three @react-three/fiber @react-three/drei
pnpm --dir web add -D @types/three @playwright/test
```

Replace the example page with a heading `Nereid Ocean Investigation` and retain the working Vitest configuration.

- [ ] **Step 3: Add one smoke test before product code**

```tsx
// web/src/app/page.test.tsx
import { render, screen } from '@testing-library/react'
import Page from './page'

it('identifies the investigation workspace', () => {
  render(<Page />)
  expect(screen.getByRole('heading', { name: 'Nereid Ocean Investigation' })).toBeDefined()
})
```

- [ ] **Step 4: Run foundation checks**

Run:

```bash
uv sync --all-packages
pnpm --dir web test
pnpm --dir web lint
```

Expected: dependency lock succeeds; the page test and lint pass.

- [ ] **Step 5: Commit**

```bash
git add .gitignore .python-version .env.example package.json pnpm-workspace.yaml pyproject.toml uv.lock api pipeline web
git commit -m "build: establish Nereid workspaces"
```

---

### Task 2: QC-aware NetCDF normalization and provenance

**Files:**

- Create: `pipeline/src/nereid_pipeline/manifest.py`
- Create: `pipeline/src/nereid_pipeline/normalize.py`
- Create: `pipeline/src/nereid_pipeline/cli.py`
- Create: `pipeline/tests/conftest.py`
- Create: `pipeline/tests/test_normalize.py`
- Create: `pipeline/tests/test_manifest.py`
- Create: `data/README.md`

**Interfaces:**

- Produces: `sha256_file(path: Path) -> str`.
- Produces: `normalize_profile_file(source: Path, output_dir: Path, provenance: SourceManifest) -> NormalizationResult`.
- Produces: `profiles.parquet`, `levels.parquet`, and `manifest.jsonl`.
- Parquet profile key: `(wmo: str, cycle: int, direction: str)`.
- Parquet level fields: `wmo`, `cycle`, `direction`, `pressure_dbar`, `depth_m`, `temperature_raw`, `temperature_adjusted`, `temperature_best`, `temperature_qc`, `salinity_raw`, `salinity_adjusted`, `salinity_best`, `salinity_qc`, `adjusted_pressure_error`, `data_mode`, `source_sha256`.

- [ ] **Step 1: Generate a deterministic ARGO-shaped NetCDF test fixture**

Create an xarray dataset with one profile, six pressure levels, raw and adjusted temperature/salinity values, QC values `1,1,2,3,4,1`, WMO `1900001`, cycle `7`, direction `A`, latitude `10`, longitude `70`, and timestamp `2023-03-15T00:00:00`. Write it to a temporary `.nc` file in `pipeline/tests/conftest.py`; do not download during tests.

- [ ] **Step 2: Write failing preservation and QC-selection tests**

```python
# pipeline/tests/test_normalize.py
from nereid_pipeline.normalize import normalize_profile_file


def test_normalization_preserves_provenance_and_best_values(argo_nc, tmp_path, source_manifest):
    result = normalize_profile_file(argo_nc, tmp_path, source_manifest)
    levels = result.levels.to_pandas()
    assert result.profile_count == 1
    assert levels["wmo"].unique().tolist() == ["1900001"]
    assert levels["source_sha256"].nunique() == 1
    assert levels.loc[0, "temperature_best"] == levels.loc[0, "temperature_adjusted"]
    assert levels["temperature_qc"].tolist() == [1, 1, 2, 3, 4, 1]
```

```python
# pipeline/tests/test_manifest.py
from nereid_pipeline.manifest import sha256_file


def test_sha256_is_stable(tmp_path):
    path = tmp_path / "sample.nc"
    path.write_bytes(b"argo")
    assert sha256_file(path) == "774113f725e8622bcdb91dde0a36221bedf7cb2623a39f1218f17cf6ed246d19"
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
uv run --project pipeline pytest pipeline/tests/test_manifest.py pipeline/tests/test_normalize.py -v
```

Expected: FAIL because `nereid_pipeline.manifest` and `normalize` do not exist.

- [ ] **Step 4: Implement immutable provenance and normalization**

Define frozen dataclasses:

```python
@dataclass(frozen=True)
class SourceManifest:
    source_url: str
    snapshot_doi: str
    fetched_at: datetime
    sha256: str


@dataclass(frozen=True)
class NormalizationResult:
    profiles: pyarrow.Table
    levels: pyarrow.Table
    profile_count: int
    level_count: int
```

`normalize_profile_file` must decode byte/string QC values to integers, preserve all rows, use adjusted values when finite, calculate TEOS-10 depth with `-gsw.z_from_p(pressure, latitude)`, reject duplicate `(wmo, cycle, direction, pressure_dbar)` keys, and write Parquet atomically through a temporary file and rename.

The CLI accepts only explicit bounded inputs:

```text
nereid-prepare --netcdf FILE --output data/snapshots/indian-ocean-2023-03 --source-url URL --snapshot-doi DOI
```

- [ ] **Step 5: Prove idempotency**

Add a test that runs normalization twice into the same output directory and asserts identical checksums and row counts, not appended duplicates.

- [ ] **Step 6: Run pipeline tests**

Run:

```bash
uv run --project pipeline pytest -v
```

Expected: all pipeline tests pass.

- [ ] **Step 7: Commit**

```bash
git add pipeline data/README.md
git commit -m "feat: normalize ARGO profiles with provenance"
```

---

### Task 3: Scientific contracts and deterministic analytics

**Files:**

- Create: `api/src/nereid_api/models.py`
- Create: `api/src/nereid_api/analytics.py`
- Create: `api/tests/test_models.py`
- Create: `api/tests/test_analytics.py`

**Interfaces:**

- Produces: `QueryPlan`, `QcPolicy`, `Provenance`, `QcSummary`, `MethodRecord`, `ProfileSeries`, `DerivedMetric`, and `ResultEnvelope` Pydantic models.
- Produces: `principal_thermocline(depth_m, conservative_temperature) -> DerivedMetric | None`.
- Produces: `strongest_salinity_gradient(depth_m, absolute_salinity) -> DerivedMetric | None`.

- [ ] **Step 1: Write failing query-boundary tests**

```python
# api/tests/test_models.py
import pytest
from pydantic import ValidationError
from nereid_api.models import QueryPlan


def test_query_plan_rejects_unbounded_request():
    with pytest.raises(ValidationError):
        QueryPlan(operation="find_profiles", row_limit=1000)


def test_query_plan_caps_rows():
    with pytest.raises(ValidationError):
        QueryPlan(
            operation="find_profiles",
            bbox=(60, 0, 80, 20),
            start_date="2023-03-01",
            end_date="2023-03-31",
            parameters=["TEMP", "PSAL"],
            qc_mode="research",
            row_limit=100001,
        )
```

- [ ] **Step 2: Implement exact model constraints**

`QueryPlan` uses literal operations, a `(west, south, east, north)` tuple, ISO dates, allow-listed parameters `TEMP`, `PSAL`, `PRES`, an enum QC policy, WMO/cycle selectors, and `row_limit` between 1 and 100000. A model validator requires either `(bbox + start_date + end_date)` or `(wmo + cycle)`.

`ResultEnvelope` contains these required fields:

```python
class ResultEnvelope(BaseModel):
    query_plan: QueryPlan
    data: list[dict[str, JsonValue]]
    chart_spec: list[dict[str, JsonValue]]
    provenance: list[Provenance]
    qc_summary: QcSummary
    methods: list[MethodRecord]
    assumptions: list[str]
    warnings: list[str]
    answer: str | None = None
```

- [ ] **Step 3: Write failing reference-cast tests**

Use depths `[0, 10, 20, 30, 40, 60, 100]`, Conservative Temperature `[28, 27.8, 27.5, 24, 20, 18, 15]`, and Absolute Salinity `[34, 34.1, 34.2, 34.6, 35.2, 35.3, 35.4]`. Assert thermocline depth is within one native interval of 30m, salinity-gradient depth is within one interval of 40m, units are present, uncertainty is positive, and fewer than four valid levels returns `None`.

- [ ] **Step 4: Implement analytics**

Convert arrays to finite sorted NumPy arrays, reject fewer than four unique depths or vertical span below 50m, calculate gradients with `numpy.gradient(value, depth)`, restrict thermocline candidates to 10–500m, select the strongest negative temperature gradient and strongest absolute salinity gradient, and set uncertainty to half the larger adjacent spacing. Record algorithm names and parameters in each `DerivedMetric`.

- [ ] **Step 5: Run API model and analytics tests**

Run:

```bash
uv run --project api pytest api/tests/test_models.py api/tests/test_analytics.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add api/src/nereid_api/models.py api/src/nereid_api/analytics.py api/tests
git commit -m "feat: add bounded scientific query contracts"
```

---

### Task 4: DuckDB store and FastAPI winning workflow

**Files:**

- Create: `api/src/nereid_api/store.py`
- Create: `api/src/nereid_api/service.py`
- Create: `api/src/nereid_api/main.py`
- Create: `api/tests/test_store.py`
- Create: `api/tests/test_api.py`

**Interfaces:**

- Consumes: Task 2 Parquet schemas and Task 3 models/analytics.
- Produces: `ArgoStore.find_profiles(plan: QueryPlan) -> list[dict]`, `ArgoStore.get_profile(wmo: str, cycle: int, qc_mode: QcPolicy) -> list[dict]`, and `ArgoStore.compare_profiles(profile_ids: list[tuple[str, int]], qc_mode: QcPolicy) -> list[dict]`.
- Produces: `POST /v1/query/execute`, `POST /v1/sections/derive`, `GET /v1/profiles/{wmo}/{cycle}`, and `GET /health`.

- [ ] **Step 1: Write failing bounded-store tests**

Create temporary profile/level Parquet tables from PyArrow. Test that research mode returns only adjusted QC=1 rows, exploratory mode includes QC=2, QC=3/4 never returns, bbox/date filters work, and `row_limit` is honored.

- [ ] **Step 2: Implement parameterized DuckDB queries**

`ArgoStore` receives a snapshot directory. It opens an in-memory DuckDB connection, creates read-only views over the two Parquet files, and executes fixed SQL templates selected by `QueryPlan.operation`. Bind every value as a parameter. Do not concatenate user/model strings into SQL. Validate snapshot files before opening and raise `SnapshotUnavailable` with their expected paths.

- [ ] **Step 3: Write failing API envelope test**

```python
# api/tests/test_api.py
from fastapi.testclient import TestClient
from nereid_api.main import create_app


def test_execute_returns_scientific_receipt(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post("/v1/query/execute", json={
        "operation": "find_profiles",
        "bbox": [60, 0, 80, 20],
        "start_date": "2023-03-01",
        "end_date": "2023-03-31",
        "parameters": ["TEMP", "PSAL"],
        "qc_mode": "research",
        "row_limit": 10000,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"][0]["sha256"]
    assert body["qc_summary"]["rejected"] >= 1
    assert body["methods"]
    assert body["warnings"] == []
```

- [ ] **Step 4: Implement service dispatch and HTTP errors**

`InvestigationService.execute(plan)` dispatches only allow-listed operations, calculates profile metrics when levels are present, and builds one `ResultEnvelope`. `derive_section` interpolates vertically within each selected profile, orders profiles by observation time, masks cells where neighboring profiles exceed the configured time/distance gap, and returns observation coordinates beside the grid. Map missing snapshots to HTTP 503, no matches to a successful empty envelope with one widening suggestion, invalid plans to HTTP 422, and oversized requests to HTTP 422. Add CORS only for the configured web origin.

- [ ] **Step 5: Run API tests and type diagnostics**

Run:

```bash
uv run --project api pytest -v
```

Expected: store and API tests pass without network access.

- [ ] **Step 6: Commit**

```bash
git add api/src/nereid_api api/tests
git commit -m "feat: expose reproducible ARGO investigations"
```

---

### Task 5: Linked investigation workspace

**Files:**

- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/globals.css`
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/api.ts`
- Create: `web/src/components/InvestigationWorkspace.tsx`
- Create: `web/src/components/QueryControls.tsx`
- Create: `web/src/components/QueryPlanPanel.tsx`
- Create: `web/src/components/ProfilePlot.tsx`
- Create: `web/src/components/CrossSectionPlot.tsx`
- Create: `web/src/components/ScientificReceipt.tsx`
- Create: `web/src/components/InvestigationWorkspace.test.tsx`

**Interfaces:**

- Consumes: `POST /v1/query/execute` and the exact snake_case `ResultEnvelope` JSON contract.
- Produces: one accessible investigation workspace with explicit filters and no required LLM.

- [ ] **Step 1: Define the browser contract**

Mirror only the Task 3 response fields in `types.ts`. Add `executeQuery(plan: QueryPlan, signal?: AbortSignal): Promise<ResultEnvelope>` that sends JSON, throws `ApiError(status, message)` for non-2xx responses, and respects `NEXT_PUBLIC_API_URL`.

- [ ] **Step 2: Write failing interaction test**

Mock `executeQuery`, render the workspace, choose the curated March 2023 question, submit, and assert the parsed bbox/time/QC policy, WMO/cycle, retained/rejected counts, source DOI, and method name appear. Add a second test where the API returns no matches and assert a non-destructive widening suggestion appears.

- [ ] **Step 3: Build the minimum workspace**

Use native form controls and CSS rather than a component library. The default query is the winning question. Keep the visible hierarchy: query and filters, parsed plan, visualization area, profiles, scientific receipt. Disable only the submit button while loading; preserve previous results until the replacement succeeds. Abort an in-flight request when a new one begins.

`ProfilePlot` uses responsive SVG: map depth to a downward-increasing y-axis, temperature and salinity to separate x scales, render observation points, and include units in accessible labels. A raw-versus-best-adjusted control switches displayed fields without discarding either source value. `CrossSectionPlot` renders the server-provided grid, leaves masked cells empty, overlays observation coordinates, and exposes the same values in an accessible table. Neither plot smooths unsupported gaps.

- [ ] **Step 4: Run frontend tests and lint**

Run:

```bash
pnpm --dir web test
pnpm --dir web lint
pnpm --dir web build
```

Expected: tests, lint, and production build pass.

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: build the Nereid investigation workspace"
```

---

### Task 6: Four-dimensional trajectory renderer and performance proof

**Files:**

- Create: `web/src/lib/geometry.ts`
- Create: `web/src/lib/benchmark-data.ts`
- Create: `web/src/components/TrajectoryGlobe.tsx`
- Create: `web/src/components/TrajectoryFallback.tsx`
- Create: `web/src/components/TimeController.tsx`
- Create: `web/src/lib/geometry.test.ts`
- Create: `web/e2e/rendering.spec.ts`
- Modify: `web/src/components/InvestigationWorkspace.tsx`

**Interfaces:**

- Consumes: trajectory rows containing `longitude`, `latitude`, `depth_m`, `timestamp`, `wmo`, and `cycle`.
- Produces: `toGlobePosition(longitude, latitude, depthM, exaggeration) -> [number, number, number]`.
- Produces: a WebGL point/line renderer with a time cutoff and a labeled vertical-exaggeration control.

- [ ] **Step 1: Write failing geometry tests**

Assert longitude/latitude cardinal points map to the expected unit-sphere axes, depth decreases radius, exaggeration changes only radial depth, and invalid coordinates/depth are rejected.

- [ ] **Step 2: Implement geometry and typed-array buffers**

Convert geographic coordinates to sphere coordinates. Build one `Float32Array` for positions and one for colors. Render with one React Three Fiber `<points>`/`bufferGeometry` draw call using `bufferAttribute`; selected profiles may use a separate line. Use `Canvas frameloop="demand"`, invalidate after time/filter changes, and dispose geometries on replacement.

- [ ] **Step 3: Add truthful 4D controls and fallback**

Time controls filter by timestamp without mutating source rows. Display longitude, latitude, depth, time, total points, rendered points, and exaggeration. `TrajectoryFallback` is an SVG longitude/latitude projection with keyboard-selectable points and appears for reduced motion, WebGL failure, or an explicit 2D toggle.

- [ ] **Step 4: Add a deterministic 100,000-point benchmark**

`benchmark-data.ts` creates deterministic points using a fixed linear-congruential sequence and labels them `benchmark only`; they never enter scientific results. The Playwright test loads `/?benchmark=100000`, waits for a `data-render-ready` marker, records initialization time and browser FPS over five seconds, and writes JSON to `docs/evidence/rendering.json`. The UI must report the declared browser and hardware separately from measured values.

- [ ] **Step 5: Verify rendering**

Run:

```bash
pnpm --dir web test
pnpm --dir web build
pnpm --dir web exec playwright test e2e/rendering.spec.ts
```

Expected: geometry tests pass, build passes, and benchmark evidence exists. If measured FPS is below 30, reduce visible point size and update buffers in place; do not falsify the result.

- [ ] **Step 6: Commit**

```bash
git add web docs/evidence/rendering.json
git commit -m "feat: render ARGO trajectories through space and time"
```

---

### Task 7: Optional Azure OpenAI typed planner

**Files:**

- Create: `api/src/nereid_api/planner.py`
- Create: `api/tests/test_planner.py`
- Modify: `api/src/nereid_api/main.py`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/components/QueryControls.tsx`

**Interfaces:**

- Consumes: Task 3 `QueryPlan` model.
- Produces: `ExplicitPlanner.plan(filters: QueryPlan) -> QueryPlan`.
- Produces: `AzurePlanner.plan(question: str) -> QueryPlan` using `AsyncAzureOpenAI` and Pydantic parsing.
- Produces: `POST /v1/query/plan` returning `{plan, planner, warnings}`.

- [ ] **Step 1: Write planner tests before credentials or network**

Test explicit passthrough, rejection of an unbounded model response, correct handling of a refusal/missing parsed output, timeout mapping, and absence of Azure configuration. Use a fake client object; tests never call a model.

- [ ] **Step 2: Implement Azure configuration and typed parsing**

Instantiate `AsyncAzureOpenAI` only when all required environment variables exist. Set a 15-second timeout and one retry. Call `client.chat.completions.parse(model=deployment, response_format=QueryPlan, messages=[system, user])`. The system message lists allowed operations/parameters, demands bounded geography and dates, and instructs the model to make no scientific claims. Re-validate the parsed plan locally before returning it.

- [ ] **Step 3: Expose graceful planner behavior**

If Azure is unconfigured or unavailable, return HTTP 200 with `planner="explicit"`, no plan generated from text, and a warning instructing the browser to use explicit filters. Never substitute a fabricated plan. Add a visible “AI interpretation unavailable—filters still work” state.

- [ ] **Step 4: Verify backend and frontend**

Run:

```bash
uv run --project api pytest api/tests/test_planner.py api/tests/test_api.py -v
pnpm --dir web test
pnpm --dir web build
```

Expected: all checks pass with no Azure credentials.

- [ ] **Step 5: Commit**

```bash
git add api web
git commit -m "feat: add optional typed Azure query planning"
```

---

### Task 8: Evidence export, offline replay, and final acceptance gate

**Files:**

- Create: `api/src/nereid_api/export.py`
- Create: `api/tests/test_export.py`
- Create: `web/e2e/winning-flow.spec.ts`
- Create: `docs/evidence/README.md`
- Create: `docs/evidence/query-cases.json`
- Create: `docs/evidence/acceptance.md`
- Modify: `api/src/nereid_api/main.py`
- Modify: `web/src/components/ScientificReceipt.tsx`
- Modify: `data/README.md`

**Interfaces:**

- Consumes: `ResultEnvelope` and selected level rows.
- Produces: `build_evidence_zip(envelope, rows) -> bytes` containing `selection.csv`, `provenance.json`, `query-plan.json`, and `methods.json`.
- Produces: `POST /v1/export` and a download action.

- [ ] **Step 1: Write failing export integrity test**

Build a known envelope and two rows. Open the returned ZIP in memory and assert exact filenames, CSV row count, units, WMO/cycle, source checksum, query plan, QC counts, and method parameters match the input.

- [ ] **Step 2: Implement deterministic evidence export**

Sort rows by WMO, cycle, timestamp, and pressure before writing. Use UTF-8 CSV and stable JSON key ordering. Include a `README.txt` that states the Argo citation, snapshot DOI, generation timestamp, and that the export is a selected derivative rather than a lossless original NetCDF replacement.

- [ ] **Step 3: Add the 30-case query evaluation set**

`query-cases.json` contains exactly 30 questions with expected operation, bbox or WMO/cycle, date window, parameters, and QC mode. Include five invalid/unbounded/injection-like questions whose expected result is rejection. The evaluation script reports correct operation/filter selection and must reach at least 27/30 without weakening validators.

- [ ] **Step 4: Add winning-flow Playwright coverage**

Start the API against the committed fixture snapshot and the web app. Submit the March 2023 workflow, select two profiles, confirm depth plots and 4D metadata, inspect provenance/QC/methods, download the ZIP, and validate its filenames. Repeat with outbound network disabled. The test must fail if any synthetic fallback measurement appears.

- [ ] **Step 5: Run the complete acceptance gate**

Run:

```bash
uv run --project pipeline pytest -v
uv run --project api pytest -v
pnpm --dir web test
pnpm --dir web lint
pnpm --dir web build
pnpm --dir web exec playwright test
```

Record exact command outputs, dataset row/profile counts, machine/browser identity, warm-cache latency, planner score, and rendering result in `docs/evidence/acceptance.md`. Do not describe a target as achieved unless its command produced the evidence.

- [ ] **Step 6: Review originality and repository hygiene**

Run secret scanning available on the machine, inspect `git status`, verify generated snapshots and `.env` are ignored, verify third-party license notices, and confirm no file was copied from the audited FloatChat repositories.

- [ ] **Step 7: Commit**

```bash
git add api web data docs/evidence .gitignore
git commit -m "feat: prove the offline Nereid investigation flow"
```

## Final Stop Condition

Stop implementation when the pinned real-data workflow, deterministic scientific receipt, 4D renderer, export, offline replay, and measured acceptance gate pass. Do not add auth, voice, collaboration, forecasting, extra datasets, or visual pages unless the submitted judging rubric explicitly requires them.
