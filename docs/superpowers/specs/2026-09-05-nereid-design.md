# Nereid: Scientific ARGO Investigation Engine

**Status:** Proposed for implementation  
**Date:** 2026-09-05  
**Challenge:** ORION 1.0 — ORION-PS-01 FloatChat  
**Team:** Four people; data-science lead, data pipeline, API/AI, and visualization

## Purpose

Nereid will let researchers and policy analysts ask plain-language questions about ARGO ocean profiles and receive reproducible maps, depth plots, derived measurements, and source citations. The product will distinguish itself from existing FloatChat submissions by making every numerical answer auditable and scientifically honest.

The first complete workflow will answer:

> Compare reliable temperature and salinity structure for floats near 10°N, 70°E in March 2023.

The interface will show the interpreted filters, matching float trajectories, two quality-controlled depth profiles, thermocline and salinity-gradient estimates, uncertainty and coverage warnings, and an export containing the selected data and provenance.

## Goals

- Ingest real ARGO NetCDF files from a documented GDAC source.
- Preserve raw values, adjusted values, quality flags, errors, data modes, float identity, cycle, position, time, and file provenance.
- Translate natural language into a constrained, visible query plan.
- Perform filtering and ocean calculations deterministically outside the language model.
- Render linked longitude, latitude, depth, and time data through WebGL.
- Provide a scientific receipt with every result.
- Work from a pinned local snapshot when event internet access is unavailable.
- Leave behind measurable evidence for query accuracy, scientific correctness, latency, and 100,000-point rendering performance.

## Non-goals

The first release will not include authentication, team workspaces, voice input, unrestricted generated SQL, social features, forecasting, global-scale continuous ingestion, or a general-purpose ocean-data assistant. It will not label sparse moving-float observations as marine heatwaves. It may report subsurface warm-anomaly candidates with an explicit method and limitation.

## Architecture

The repository will contain three product areas:

```text
floatchat/
├── web/       Next.js user interface and WebGL visualization
├── api/       FastAPI query, analytics, and export service
├── pipeline/  ARGO discovery, download, NetCDF conversion, and validation
├── data/      ignored runtime data plus small committed test fixtures
└── docs/      design, research, methods, and judging evidence
```

### Data layer

1. The pipeline queries a GDAC/argopy index using bounded geography, time, and parameter filters.
2. Downloaded NetCDF files remain immutable and receive a manifest entry containing source URL, checksum, fetch time, snapshot DOI, WMO, and cycle.
3. Python, xarray, argopy, and TEOS-10 GSW create normalized profile and level Parquet files.
4. DuckDB queries Parquet for the initial deployment and offline demo. This avoids a database service during judging while supporting the required scale. PostgreSQL/PostGIS is a documented production migration, not part of the initial build.
5. Vector search is restricted to textual metadata and glossary documents. Numerical measurements are queried structurally.

### API and query layer

FastAPI exposes a small set of typed operations:

- `find_profiles`: bounded geography, date, parameters, and QC policy.
- `nearest_floats`: location, count, and time window.
- `get_profile`: WMO, cycle, and selected variables.
- `compare_profiles`: selected profile identifiers.
- `derive_section`: selected profiles, interpolation limits, and method version.
- `export_selection`: CSV plus provenance JSON, with a NetCDF subset where practical.

The language model may produce only a validated `QueryPlan` JSON object. The plan uses allow-listed operations, fields, units, bounded dates, bounding boxes, row limits, and enumerated QC policies. The server executes parameterized deterministic handlers; the model never emits executable SQL or supplies numerical facts.

If Azure OpenAI credentials are unavailable, explicit filters and curated example questions remain fully functional. This fallback is visible and does not invent data.

### Analytics layer

Research mode prefers delayed adjusted observations with QC=1 and checks adjusted error. Exploratory mode may include QC=2 and labels the result accordingly. QC=3/4 measurements never enter scientific outputs.

For each ascending profile, the service will:

- sort and deduplicate pressure levels;
- convert pressure, position, Practical Salinity, and in-situ temperature through TEOS-10;
- estimate depth and Conservative Temperature;
- calculate the principal thermocline from the strongest sustained negative temperature gradient within 10–500m;
- calculate the strongest absolute salinity gradient while preserving its sign;
- report native spacing, coverage, algorithm parameters, and uncertainty;
- return insufficient evidence when coverage or gradient requirements fail.

A warm-anomaly feature may compare depth-binned observations with a declared baseline. It will be named a warm-anomaly candidate, not a marine heatwave, unless a daily gridded dataset and a valid multi-decade climatology are added later.

### Web interface

The application has one investigation workspace rather than separate decorative pages:

- A query bar with curated examples and explicit filter controls.
- A visible parsed-query panel that users can correct before execution.
- A React Three Fiber globe rendering float trajectories with longitude, latitude, depth, and a time controller. Vertical exaggeration is labeled.
- Linked temperature and salinity depth-profile plots.
- A cross-section view that masks unsupported gaps and shows observation locations.
- A raw-versus-adjusted toggle demonstrating the effect of quality control.
- A scientific receipt listing source, DOI, WMO/cycles, query plan, units, QC counts, methods, assumptions, freshness, and warnings.
- Accessible keyboard operation, non-color-only status cues, a colorblind-safe palette, depth axes increasing downward, and a reduced-motion/2D fallback.

## Data flow

```text
Question or explicit filters
  → validated QueryPlan
  → bounded DuckDB query over normalized Parquet
  → deterministic analytics
  → result envelope
  → linked WebGL and chart views
  → optional language summary derived only from returned fields
```

Every result envelope contains `data`, `chartSpec`, `provenance`, `qcSummary`, `methods`, `assumptions`, `warnings`, and an optional `answer`. Numerical statements in `answer` must reference fields in the same envelope.

## Failure behavior

- Upstream unavailable: use the pinned snapshot and display its timestamp and DOI.
- Snapshot unavailable: stop with setup instructions; never generate replacement measurements.
- No matching profiles: preserve the query and suggest widening one bounded filter.
- Inadequate vertical coverage: show observations but withhold derived thermocline/gradient values.
- Invalid model plan: reject it and request correction; do not partially execute it.
- Model unavailable or rate-limited: keep explicit filters and deterministic queries working.
- Oversized query: reject before execution and state the applicable bound.
- Visualization overload: apply visible level-of-detail sampling while retaining selected profiles exactly and reporting rendered versus total points.

## Security and cost controls

- Keep all credentials server-side and out of Git history.
- Use allow-listed typed tools, Pydantic validation, row limits, request timeouts, and read-only data access.
- Treat dataset text and metadata as untrusted model input.
- Cache identical query plans and explanations.
- Make the language-model feature optional so the scientific application has no mandatory token cost.
- Run secret and dependency scans before submission.

## Verification

The smallest durable checks are:

1. A hand-audited NetCDF fixture proving preservation of identity, modes, QC, adjusted errors, and provenance.
2. Idempotent ingestion with no duplicate profile keys.
3. Synthetic reference casts proving thermocline and salinity-gradient estimates within one native vertical interval and proving refusal on inadequate coverage.
4. Thirty natural-language cases; at least 27 select the correct operation and filters.
5. Fifteen deterministic API cases with exact expected results.
6. Injection, mutation, unbounded-query, and unsupported-unit plans are rejected.
7. Every result includes provenance and reports retained/rejected observations.
8. Warm-cache metadata queries complete below one second p95 and end-to-end deterministic analysis below three seconds on declared hardware.
9. The visualization sustains at least 30 FPS with 100,000 points on the declared demo laptop.
10. The complete demonstration replays with the network disabled after the snapshot is prepared.

These targets will be measured by checked-in scripts and captured in `docs/evidence/`; they will not be claimed from manual impressions.

## Team ownership

- **Team lead / data science:** validates scientific methods, fixtures, results, citations, and pitch.
- **Pipeline:** discovery, NetCDF manifests, normalization, QC, and reproducible snapshots.
- **API / AI:** typed query contracts, DuckDB handlers, analytics endpoints, Azure OpenAI adapter, and safety limits.
- **Visualization:** investigation workspace, WebGL trajectory renderer, linked charts, accessibility, and demo reliability.

A shared result-envelope contract is fixed before parallel implementation. Everyone contributes gold queries and rehearses the final defense.

## Delivery order

1. Establish repository checks and the result-envelope contract.
2. Prove one real NetCDF file can be ingested, queried, and traced to its source.
3. Implement and test deterministic profile analytics.
4. Expose typed API operations.
5. Build the linked investigation workspace and explicit filters.
6. Add the constrained language planner.
7. Add 4D rendering, level of detail, offline replay, exports, and evidence capture.
8. Polish only the winning workflow; defer unrelated features.

## Originality policy

Existing FloatChat repositories are competitive references only. The team will not copy their code, layouts, prompts, screenshots, generated datasets, or branding. Interfaces and methods will be derived from official ARGO, NetCDF, TEOS-10, argopy, and ERDDAP documentation. Third-party dependencies and assets will retain their licenses and notices. Commit history will document independent development and individual contributions.

## Acceptance condition

The design is implemented when a clean checkout can prepare or use the pinned snapshot, run the test suite, start the API and web app, execute the winning question, render linked real-data views, display a complete scientific receipt, export the selected evidence, and repeat that demonstration offline without synthetic measurements.
