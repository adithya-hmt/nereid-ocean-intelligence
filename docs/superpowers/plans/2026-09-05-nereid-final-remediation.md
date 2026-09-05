# Nereid Final Scientific Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every Critical and Important finding from the full `7ef7dee...c2012fb` branch review without weakening Nereid’s evidence-first constraints.

**Architecture:** First make the normalized snapshot scientifically authoritative by preserving pressure QC and computing TEOS-10 values. Then deepen the typed query contract so every advertised operation has one valid selector and deterministic implementation. Finally wire exact profile-representation selection, per-profile metrics, and derived sections into the single investigation workspace.

**Tech Stack:** Python 3.12, xarray, GSW-Python, PyArrow, DuckDB, Pydantic, FastAPI, Next.js, React, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-05-nereid-design.md`

## Global Constraints

- Real ARGO measurements only outside test fixtures; preserve official source files, checksums, DOI, acquisition timestamps, representations, raw/adjusted values, QC, and errors.
- Research mode uses adjusted values with adjusted QC 1; exploratory mode may include adjusted QC 2; QC 3/4 never enters scientific outputs.
- The language model may emit only a locally validated `QueryPlan`; never SQL or numerical analysis.
- Every numerical result remains deterministic and carries provenance, QC counts, methods, assumptions, and warnings.
- Keep the application offline-capable after preparing the pinned snapshot.
- Do not add auth, voice, collaboration, forecasting, extra datasets, pages, or synthetic scientific fallbacks.

---

### Task R1: Scientifically correct normalization and profile metrics

**Files:**
- Modify: `pipeline/src/nereid_pipeline/normalize.py`
- Modify: `pipeline/src/nereid_pipeline/cli.py`
- Modify: `pipeline/tests/conftest.py`
- Modify: `pipeline/tests/test_normalize.py`
- Modify: `api/src/nereid_api/store.py`
- Modify: `api/src/nereid_api/service.py`
- Modify: `api/src/nereid_api/analytics.py`
- Modify: `api/src/nereid_api/models.py`
- Modify: `api/tests/conftest.py`
- Modify: `api/tests/test_analytics.py`
- Modify: `api/tests/test_store.py`
- Modify: `api/tests/test_api.py`
- Modify: `data/README.md`
- Regenerate: `data/snapshots/indian-ocean-2023-03/{profiles.parquet,levels.parquet,manifest.jsonl}`

**Interfaces:**
- Produce: `normalize_profile_files(inputs: Sequence[tuple[Path, SourceManifest]], output_dir: Path) -> NormalizationResult`.
- Preserve wrapper: `normalize_profile_file(source, output_dir, provenance) -> NormalizationResult` delegates to the multi-file function.
- Level rows add `pressure_raw`, `pressure_adjusted`, `pressure_best`, `pressure_qc`, `pressure_adjusted_qc`, `pressure_adjusted_error`, `absolute_salinity`, and `conservative_temperature`.
- `absolute_salinity = gsw.SA_from_SP(PSAL_ADJUSTED, PRES_ADJUSTED, longitude, latitude)` and `conservative_temperature = gsw.CT_from_t(absolute_salinity, TEMP_ADJUSTED, PRES_ADJUSTED)` only where required inputs are finite.
- Analytics consume TEOS-10 fields, never renamed in-situ/Practical values.

- [ ] **Step 1: Add failing preservation and TEOS-10 reference tests**

Create fixture values with distinct `PRES`/`PRES_ADJUSTED`, all pressure QC/error fields, and known longitude/latitude. Assert normalized SA/CT against direct `gsw.SA_from_SP`/`gsw.CT_from_t` calls at `rtol=1e-10`; assert raw and adjusted pressure metadata survive exactly. Add a QC regression where temperature/salinity QC is 1 but pressure adjusted QC is 4 and prove the row is excluded from research and exploratory outputs.

- [ ] **Step 2: Add failing multi-file/idempotency and acquisition-time tests**

Normalize two fixture NetCDF files in one call and assert both source representations appear once in Parquet and manifest. Re-run with reversed input order and assert deterministic identical logical rows and manifest ordering. CLI tests must require one `--fetched-at` ISO timestamp per `--netcdf`/`--source-url` pair rather than calling `datetime.now()`.

- [ ] **Step 3: Implement one atomic multi-file normalizer**

Extract one-file row collection from the current writer, concatenate in memory, sort profiles by `(wmo, cycle, direction, source_sha256, source_profile_index)` and levels by that identity plus adjusted/best pressure, validate global uniqueness, and write each Parquet/manifest output once atomically. Keep all N_PROF representations.

- [ ] **Step 4: Compute and preserve pressure/TEOS-10 fields**

Use adjusted pressure for adjusted scientific fields and depth. Keep raw and adjusted in-situ temperature and Practical Salinity under their existing honest names. Store SA in `g kg-1` and CT in `degC`. Non-finite prerequisites yield null derived values, not fabricated fallbacks.

- [ ] **Step 5: Enforce pressure-aware QC and adjusted-error reporting**

All scientific row predicates require allowed `pressure_adjusted_qc`; requested TEMP/PSAL additionally require their adjusted QC. Preserve adjusted errors and include available-count/max error values in metric method parameters and receipt warnings when absent. Never relabel error as depth uncertainty.

- [ ] **Step 6: Implement a sustained thermocline rule**

For each contiguous three-level window within 10–500 m, compute a least-squares CT slope against native depth; require a negative slope and select the most negative window. Report its center depth, half-window depth span as vertical uncertainty, algorithm `strongest_negative_three_level_regression`, and exact window/QC/error parameters. Keep salinity-gradient sign while computing it from Absolute Salinity.

- [ ] **Step 7: Regenerate the committed snapshot through the documented CLI**

Use the two committed raw GDAC files, their existing source URLs/checksums/DOI, and authoritative acquisition timestamps from the current manifest. Verify 3 representations remain and no QC 3/4 output row survives.

- [ ] **Step 8: Verify and commit**

Run focused pipeline/API scientific tests, full pipeline/API suites, `git diff --check`, then commit `fix: compute QC-aware TEOS-10 profiles`. Write `.superpowers/sdd/2026-09-05-nereid-mvp/final-r1-report.md` and a `c2012fb..HEAD` review package.

---

### Task R2: Operation-specific typed plans and deterministic dispatch

**Files:**
- Modify: `api/src/nereid_api/models.py`
- Modify: `api/src/nereid_api/planner.py`
- Modify: `api/src/nereid_api/store.py`
- Modify: `api/src/nereid_api/service.py`
- Modify: `api/src/nereid_api/main.py`
- Modify: `api/tests/test_models.py`
- Modify: `api/tests/test_store.py`
- Modify: `api/tests/test_api.py`
- Modify: `api/tests/test_planner.py`
- Modify: `docs/evidence/query-cases.json`
- Modify: `docs/evidence/evaluate_queries.py`
- Modify: `api/tests/test_query_evaluation.py`
- Modify: `web/src/lib/types.ts`

**Interfaces:**
- Add: `ProfileIdentifier(wmo: str, cycle: int, source_profile_index: int | None = None)`.
- Add to `QueryPlan`: `profile_ids: list[ProfileIdentifier]`, bounded to 2–100 when used.
- Geographic operations `find_profiles` and `nearest_floats` require bbox/start/end and reject profile selectors.
- `get_profile` requires exactly wmo/cycle and rejects geographic/profile-list selectors.
- `compare_profiles` and `derive_section` require `profile_ids`; `derive_section` calls the existing section engine with explicit representations.
- Remove `export_selection` from model-plannable `Operation`; export remains the separate server-owned endpoint.

- [ ] **Step 1: Add failing operation-selector matrix tests**

For each operation, test its valid selector and every incompatible selector. Specifically prove `find_profiles(wmo,cycle)` and `get_profile(bbox,dates)` fail Pydantic validation rather than reaching assertions/500s. Validate duplicate profile IDs and fewer than two comparison/section IDs fail.

- [ ] **Step 2: Add failing parameter-policy tests**

Test TEMP-only, PSAL-only, PRES-only, and empty/all queries. Requested fields must satisfy their QC predicates; unrequested invalid variables must serialize as null rather than leak QC 3/4. Counts remain pre-pagination and parameter-specific.

- [ ] **Step 3: Implement static parameter-aware query branches**

Choose among fixed allow-listed SQL templates/predicate fragments based only on the `Parameter` enum; bind every runtime value. Always require pressure QC. Project invalid unrequested scientific values to null. Keep no generated SQL from user/model text.

- [ ] **Step 4: Implement all advertised dispatch operations**

`nearest_floats` returns bounded representations ordered by distance from bbox center while retaining their QC-valid levels. `compare_profiles` returns the requested representation groups and metrics. `derive_section` converts explicit identifiers into `SectionRequest` and returns the existing full receipt. Unsupported operation states must be impossible after validation.

- [ ] **Step 5: Update planner schema/prompt/corpus**

Enumerate only executable query operations. Replace single-ID compare/section expectations with complete `profile_ids`. Ensure evaluator compares exact list contents and all required fields. Keep real Azure evaluation blocked when credentials are absent.

- [ ] **Step 6: Verify and commit**

Run model/store/API/planner/evaluator tests and full API suite. Commit `fix: execute every bounded query plan`. Write `final-r2-report.md` and scoped review package.

---

### Task R3: Complete the linked winning investigation workflow

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/components/InvestigationWorkspace.tsx`
- Modify: `web/src/components/ProfilePlot.tsx`
- Modify: `web/src/components/CrossSectionPlot.tsx`
- Modify: `web/src/components/ScientificReceipt.tsx`
- Create: `web/src/components/ProfileMetrics.tsx`
- Modify: `web/src/components/InvestigationWorkspace.test.tsx`
- Modify: `web/src/components/ScientificReceipt.test.tsx`
- Modify: `web/e2e/winning-flow.spec.ts`
- Modify: `docs/evidence/acceptance.md`

**Interfaces:**
- Add: `deriveSection(request: SectionRequest, signal?: AbortSignal) -> Promise<ResultEnvelope>`.
- Workspace owns selected `ProfileIdentifier[]`; profile plots, metric cards, section request, and export share that exact state.
- `ProfilePlot` renders one labeled SVG/table per selected representation and names both variables/units accessibly.
- `ProfileMetrics` renders thermocline/salinity estimates, units, uncertainty, algorithm, QC label, and explicit insufficient-evidence warnings per representation.

- [ ] **Step 1: Add failing linked-selection tests**

Given three representations, select exactly two and assert only those two profile plots and metric groups render. Replace the result and prove selection resets. Assert SVG accessible names include Conservative Temperature (°C) and Absolute Salinity (g kg⁻¹).

- [ ] **Step 2: Add failing metric/refusal tests**

Parse `chart_spec.profile_metrics` into a typed browser contract. Render value/depth/units/uncertainty/method/QC for present metrics. When a selected representation lacks thermocline or salinity evidence, render a named insufficient-evidence warning rather than silence.

- [ ] **Step 3: Wire exact section derivation**

Add an abortable derive-section request for the selected two-or-more representation IDs. Preserve the last valid section if replacement fails. Render the returned cross-section only; observation coordinates and masked unsupported gaps remain accessible.

- [ ] **Step 4: Render per-representation profile plots**

Do not merge different floats/representations into one unlabeled series. Keep raw-versus-best-adjusted control, depth increasing downward, separate legends/identity labels, and complete table/text alternatives.

- [ ] **Step 5: Update winning-flow E2E**

Select two representations, assert two distinct profile identities, metric values or explicit refusal, derive a section and assert masked/observed coordinates, confirm 4D metadata, then export exactly the same selections offline.

- [ ] **Step 6: Run final acceptance gate**

Run pipeline/API/web unit suites, lint, build, all Playwright, headed GPU benchmark last, evaluator (expected Azure block), tracked-file secret pattern scan, license listing, `lens_diagnostics mode=all`, and `git diff --check`. Update acceptance evidence with exact current counts/results only.

- [ ] **Step 7: Commit and final review**

Commit `fix: complete the linked scientific workflow`. Write `final-r3-report.md`, generate a full `7ef7dee...HEAD` review package, and repeat independent Standards/Spec review. Fix all Critical/Important findings; record minor findings without widening scope.

---

### Task R4: Close final scientific/API invariants

**Files:**
- Modify: `api/src/nereid_api/store.py`
- Modify: `api/src/nereid_api/service.py`
- Modify: `api/src/nereid_api/analytics.py`
- Modify: `api/tests/test_store.py`
- Modify: `api/tests/test_api.py`
- Modify: `api/tests/test_analytics.py`

- [ ] **Step 1: Add mixed-QC and parameter-mask regressions**

Prove TEMP-only research queries with salinity QC 3/4 never return Conservative Temperature derived from that salinity. Null every unrequested variable value/QC/error regardless of whether its QC is 1, 2, 3, 4, missing, or invalid. Compute thermocline only when TEMP is requested and salinity gradient only when PSAL is requested; PRES-only plans produce no variable metrics.

- [ ] **Step 2: Preserve native continuity for thermocline windows**

Build three-level regression windows before dropping QC-invalid native levels, so an invalid level breaks adjacency. Add a profile with valid levels on either side of one rejected native level and prove no window bridges it.

- [ ] **Step 3: Add adjusted-error receipt warnings**

For each selected representation and requested pressure/TEMP/PSAL field, warn when eligible measurements lack adjusted-error metadata. Keep available-count/max-error method parameters for complete metadata; do not invent uncertainty.

- [ ] **Step 4: Enforce row limits for every operation**

Apply row limits to get-profile and nearest-level outputs. Preflight exact compare/section operations against the QC-eligible level count and return HTTP 422 when the exact selection exceeds `row_limit`, rather than returning partial representations. Add boundary tests for each operation.

- [ ] **Step 5: Verify and commit**

Run focused and full API tests, then commit `fix: close scientific query invariants` and review the scoped diff.

---

### Task R5: Make metric and section rendering scientifically exact

**Files:**
- Modify: `web/src/components/ProfileMetrics.tsx`
- Modify: `web/src/components/CrossSectionPlot.tsx`
- Modify: `web/src/components/InvestigationWorkspace.test.tsx`
- Modify: `web/e2e/winning-flow.spec.ts`
- Modify: `web/src/lib/types.ts`

- [ ] **Step 1: Use canonical metric identifiers**

Match API IDs `principal_thermocline` and `strongest_salinity_gradient`; keep human labels separate. Unit tests and offline E2E must require at least one real metric from the committed snapshot rather than accepting a false insufficient-evidence fallback.

- [ ] **Step 2: Preserve exact representation and gap semantics**

Type and render observation coordinates with `source_profile_index` and `vertical_sampling_scheme`. Associate each cell with its own gap index/reason instead of `masked_gaps[0]`. Label interpolated non-null cells as derived/interpolated, never observed; observation markers alone are observed.

- [ ] **Step 3: Verify and commit**

Run focused web tests, full web tests/lint/build/offline Playwright, GPU benchmark last, reconcile evidence, commit `fix: render exact scientific evidence`, then repeat the full independent Standards/Spec review.

---

### Task R6: Close final identity, raw-QC, section-gap, and nearest-count contracts

**Files:**
- Modify: `pipeline/src/nereid_pipeline/normalize.py`
- Modify: `api/src/nereid_api/models.py`
- Modify: `api/src/nereid_api/store.py`
- Modify: `api/src/nereid_api/service.py`
- Modify: `api/src/nereid_api/main.py`
- Modify: corresponding pipeline/API tests
- Modify: `web/src/lib/types.ts`, `web/src/lib/api.ts`
- Modify: `web/src/components/InvestigationWorkspace.tsx`, `ProfilePlot.tsx`, `ProfileMetrics.tsx`, `CrossSectionPlot.tsx`, `ScientificReceipt.tsx`
- Modify: web unit/E2E tests and evidence docs

- [ ] **Step 1: Quarantine raw QC 3/4**

Requested raw TEMP/PSAL values whose own raw QC is not allowed by the selected research/exploratory policy must serialize as null and never enter plots or exports. Adjusted scientific fields continue using adjusted QC. Add mismatched raw-QC=4/adjusted-QC=1 tests through API, export, and UI.

- [ ] **Step 2: Make direction part of exact identity**

Add ascending/descending direction to `ProfileIdentifier` and carry it through every store selector/join grouping, section/export selection, receipt, client type, UI key/label, corpus expectation and E2E assertion. Keep `source_profile_index` source-local. Add collision tests for one WMO/cycle/index with A and D records.

- [ ] **Step 3: Bound vertical section interpolation**

Add `max_vertical_gap_m` to `SectionRequest` with a finite positive bound and documented default. Interpolation may use exact points or adjacent valid bracketing levels only when their depth separation is within the bound; otherwise return null and record a vertical-gap reason for that cell/pair. Never bridge a rejected native gap.

- [ ] **Step 4: Give nearest floats a separate count contract**

Add bounded `float_count` for `nearest_floats`. Select that many complete nearest representations by bbox-center distance, then return all their eligible levels only if the aggregate respects `row_limit`; otherwise reject 422 rather than truncate a representation. Add exact count/completeness and overflow tests.

- [ ] **Step 5: Render single-parameter profiles independently**

Profile panels must retain rows when only TEMP or only PSAL is requested and render each available series independently, with no insufficient-evidence message for an unrequested companion metric.

- [ ] **Step 6: Correct evidence and warnings**

Use `run_plan` in the documented latency command and either restore the truthful multiple-sampling-scheme API warning or remove the claim. Run scoped pipeline/API/web suites, offline Playwright, GPU benchmark last, evaluator expected blocked, reconcile exact evidence, and commit `fix: enforce final scientific identity contracts`.
