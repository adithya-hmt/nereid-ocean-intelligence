# Nereid — Evidence-First Ocean Intelligence

Nereid turns official ARGO float profiles into reproducible ocean investigations. It combines deterministic QC-aware ocean analytics, linked 4D visualization, optional typed AI planning, and downloadable evidence—without allowing an LLM to generate SQL or scientific claims.

## Why it is different

- **Official data only:** the committed offline demo uses two GDAC NetCDF files cited with source URLs, DOI, fetch timestamps, and SHA-256 hashes.
- **No hidden profile merging:** identity is preserved as WMO, cycle, direction, and source profile index, including multiple vertical sampling schemes.
- **Defensible science:** pressure-aware ARGO QC gates TEOS-10 Absolute Salinity and Conservative Temperature calculations. QC 3/4 values never enter scientific output.
- **Evidence with every answer:** results include provenance, retained/rejected counts, assumptions, warnings, method versions, units, adjusted-error availability, and a deterministic ZIP export.
- **Offline-first demo:** the full winning flow runs from the pinned local snapshot with outbound network requests blocked.
- **AI stays bounded:** Azure OpenAI may produce only a locally validated `QueryPlan`. Explicit controls remain fully usable without credentials.

## Demo in one command

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js, and pnpm.

```bash
uv sync --all-packages
pnpm install --frozen-lockfile
pnpm dev
```

Open **http://localhost:3100**. The API runs at **http://127.0.0.1:8000** and its health endpoint is `/health`.

1. Select **Use March 2023 example**.
2. Run the investigation.
3. Inspect separate source representations, 4D trajectory, profile metrics, and scientific receipt.
4. Select two exact representations and derive a gap-masked cross-section.
5. Download the deterministic evidence ZIP.

See [`docs/demo.md`](docs/demo.md) for the 90-second judging script.

## Architecture

```text
Official ARGO NetCDF
  → xarray + GSW/TEOS-10 normalization
  → provenance manifest + Parquet snapshot
  → parameterized DuckDB queries
  → typed FastAPI envelopes
  → Next.js + React Three Fiber investigation workspace
```

| Layer | Location | Responsibility |
|---|---|---|
| Pipeline | `pipeline/` | Atomic NetCDF normalization, source identity, QC, TEOS-10, manifests |
| API | `api/` | Validated query plans, deterministic analytics, bounded sections, evidence ZIP |
| Web | `web/` | Correctable plans, linked profiles/trajectory/sections, accessible fallbacks |
| Snapshot | `data/snapshots/indian-ocean-2023-03/` | Pinned real GDAC replay data |
| Evidence | `docs/evidence/` | Acceptance record, planner corpus, rendering benchmark |

## Scientific policy

- Research mode admits adjusted QC **1** only.
- Exploratory mode may visibly admit adjusted QC **2**.
- QC **3/4** measurements are excluded from scientific outputs in every mode.
- Conservative Temperature requires valid pressure, temperature, and salinity dependencies.
- Absolute Salinity requires valid pressure and salinity dependencies.
- Thermocline detection uses a sustained three-native-level regression and never bridges a rejected native level.
- Sections are chronological, bounded, parameter-faithful, and mask unsupported vertical, time, and distance gaps.

Nereid does not claim marine heatwave attribution from sparse profiles and does not relabel Practical Salinity or in-situ temperature as TEOS-10 quantities.

## Optional Azure planner

The product works without AI. To enable typed natural-language planning, set:

```bash
export AZURE_OPENAI_ENDPOINT=...
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_DEPLOYMENT=...
export OPENAI_API_VERSION=...
```

The planner can return only the allow-listed `QueryPlan`; the server validates it before any query. The checked-in 30-case evaluation intentionally reports **BLOCKED** when these credentials are absent—no score is fabricated.

## Validation evidence

Latest recorded release run:

- Pipeline: **7 passed**
- API: **95 passed**
- Web unit tests: **34 passed**
- Offline Playwright: **2 passed**
- Production build and lint: passed
- 100,000-point R3F benchmark: **59.684 FPS** on Intel UHD Graphics 620

Full commands and limitations are recorded in [`docs/evidence/acceptance.md`](docs/evidence/acceptance.md). Rendering details are in [`docs/evidence/rendering.json`](docs/evidence/rendering.json).

## Prepare another snapshot

```bash
uv run --project pipeline nereid-prepare \
  --netcdf path/to/profile.nc \
  --source-url https://data-argo.ifremer.fr/.../profile.nc \
  --fetched-at 2026-09-05T00:00:00Z \
  --snapshot-doi https://doi.org/10.17882/42182 \
  --output data/snapshots/my-snapshot
```

Pass each `--netcdf`, `--source-url`, and `--fetched-at` once per source file. No synthetic measurement fallback is used for scientific output.
