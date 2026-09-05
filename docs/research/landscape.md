# Research: ORION 1.0 FloatChat challenge

## Summary

ORION-PS-01 is best understood as a **2026 expansion of SIH 2025 problem 25040**, not a wholly new brief: it retains natural-language access to Argo/NetCDF, retrieval and visualization, but adds explicit 4D WebGL, thermocline/salinity-gradient sections, anomaly/heatwave detection, 100k-point rendering and latency evaluation. The public competitor field is visually ambitious but scientifically weak: most repositories either mock data, flatten NetCDF without respecting Argo modes/QC, confuse vector retrieval with numerical querying, or document components they do not ship. A winning four-person implementation should be smaller and auditable: a reproducible Indian Ocean data snapshot, QC-aware profile analytics, constrained query tools, evidence-bearing answers, and one linked map/profile/cross-section workflow.

## 1. Problem lineage and what is actually required

1. **Original lineage.** A repository snapshot explicitly identifying **SIH 2025 Problem Statement 25040** gives the title “FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization” and requires NetCDF→SQL/Parquet, PostgreSQL plus FAISS/Chroma, multimodal-LLM RAG translating natural language to SQL **using MCP**, Streamlit/Dash maps and profiles, chat, export to ASCII/NetCDF, and an Indian Ocean PoC extensible to BGC/gliders/buoys/satellites. [SIH statement transcription in iamNVN/SIH-ARGOFloat](https://github.com/iamNVN/SIH-ARGOFloat/blob/156731264ecd30fb93d755d93174ea356dc154d5/README.md)
2. **ORION adaptation.** The organizer's primary page names the track **ORION-PS-01**, changes the tagline to “Multi-Modal Semantic Query Engine & 4D Visualization,” and explicitly evaluates query/RAG grounding, 100k+ coordinate rendering, scientific utility/UX, and multi-parameter filter latency. It asks for real telemetry ingestion, a 4D portal, NetCDF multi-variable parsing, thermocline/salinity-gradient cross-sections, and automated marine heatwave/anomaly detection. [ORION 1.0 official challenge arena](https://orion.sathyabama.ac.in/#challenges)
3. **Relationship confidence.** Title, domain, inputs and conversational architecture establish derivation from SIH 25040, chronologically SIH 2025→ORION 2026. ORION does **not** display “25040” or attribute SIH on its public page, so a formal sponsorship/permission relationship cannot be asserted. “FastFloat Engine” and “ARGO NetCDF API” are named by ORION but not defined protocols/products; treat them as suggested labels, not mandatory dependencies.
4. **Round-one reality.** ORION's public FAQ asks for problem analysis, architecture, stack justification and roadmap in its fixed template; it says live twists may arrive at the finale. Therefore design extensible typed tools and a cached offline path, rather than over-fitting undocumented finale requirements. [ORION official FAQ](https://orion.sathyabama.ac.in/#faq)

## 2. Public implementation audit: evidence, not README claims

| Repository (audited revision) | What source actually implements | Material gaps / demo weakness |
| --- | --- | --- |
| [vishalbarai007/FloatChat @ `4d87765`](https://github.com/vishalbarai007/FloatChat/tree/4d877654115a91f2f4b14fb48478c9ff416fff48) | Large Next.js UI; FastAPI upload; xarray flattening; SQLite storage; Ollama intent/text-to-SQL; HTML map; bundled NetCDF and SQLite samples. | Not PostgreSQL/MCP or live GDAC; generic flattening loses Argo semantics; no explicit adjusted-variable/data-mode/QC policy; extensive surface UI does not equal scientific analytics. README says MIT but no license file was present at the audited revision. [Backend](https://github.com/vishalbarai007/FloatChat/blob/4d877654115a91f2f4b14fb48478c9ff416fff48/server/main.py) |
| [ro-lex404/FloatChat @ `d6d1761`](https://github.com/ro-lex404/FloatChat/tree/d6d1761f2385afc638c780d9b6de9f95637a52b9) | Runnable Streamlit/FastAPI PoC; static Aug-2020 summaries and FAISS; E5 embeddings; Gemini; voice; Plotly/PyDeck; live per-float argopy fetch with source fallback. | No relational SQL/MCP; vectors summarize numerical rows instead of serving metadata discovery; outage fallback is called “mock time-series”; no analysis use of QC; ingestion checks `PSAL_QC` inconsistently; static map and live detail can have different provenance. [Backend evidence](https://github.com/ro-lex404/FloatChat/blob/d6d1761f2385afc638c780d9b6de9f95637a52b9/app_4.py) |
| [lebiraja/sih25 @ `381d29d`](https://github.com/lebiraja/sih25/tree/381d29d773649a7728e613a0eaca2cb15ab91cb7) | Several partially overlapping prototypes: Parquet, PostgreSQL scripts, Chroma/Ollama RAG, generated Plotly HTML, plus a TypeScript MCP PostgreSQL server/client and React globe. | README's “22 million profiles” is actually described elsewhere as measurement rows; “sub-3 second” is unsubstantiated; multiple `newtry`/`FLOATCHART` trees increase integration risk; synthetic random profiles occur in visualization tests; no QC-aware scientific derivations. [README](https://github.com/lebiraja/sih25/blob/381d29d773649a7728e613a0eaca2cb15ab91cb7/README.md) [MCP source](https://github.com/lebiraja/sih25/blob/381d29d773649a7728e613a0eaca2cb15ab91cb7/FLOATCHART/mcp-server/src/index.ts) |
| [Aditya-Choukade/Varuna-Lens @ `7c25476`](https://github.com/Aditya-Choukade/Varuna-Lens/tree/7c254764b4d6402cf6923eb753199b5389be3223) | Polished Next.js dashboard shell. | Backend/PostgreSQL/RAG/Docker claimed in README are absent from this revision; map contains four hard-coded `F00x` points; no API/data dependencies; effectively a UI mock. [Map source](https://github.com/Aditya-Choukade/Varuna-Lens/blob/7c254764b4d6402cf6923eb753199b5389be3223/components/ocean-map.tsx) |
| [iamNVN/SIH-ARGOFloat @ `1567312`](https://github.com/iamNVN/SIH-ARGOFloat/tree/156731264ecd30fb93d755d93174ea356dc154d5) | Real one-float NetCDF sample, NetCDF→four PostgreSQL tables, SQLAlchemy schema, two MCP tools, LLM tool loop, Streamlit UI. Logs prove successful queries over **387 levels from one float**. | Not vector RAG or regional scale; committed `.env`/logs are a security/privacy smell; generated dashboard metrics and float fleets use `numpy.random`; logs expose SQL errors and tool-message failures; raw rather than adjusted core values dominate profile table. [Loader](https://github.com/iamNVN/SIH-ARGOFloat/blob/156731264ecd30fb93d755d93174ea356dc154d5/backend/data_handler.py) [MCP server](https://github.com/iamNVN/SIH-ARGOFloat/blob/156731264ecd30fb93d755d93174ea356dc154d5/backend/mcps/mcp_server.py) |
| [namang2/Floatchat-sih2025 @ `25915aa`](https://github.com/namang2/Floatchat-sih2025/tree/25915aa446b33408dd9712a8d21c55e1a6b233b3) | Broadest ingestion: core/BGC schemas preserve raw, adjusted, error and QC values; PostgreSQL, Chroma RAG, Node orchestration, Mongo chat and alerts. | Considerably too broad for four students/24 hours; anomaly detector is only global `absolute z ≥ 3`, not climatological marine heatwave science; raw LLM→SQL and auto-repair remain risky; no root README/license at audit; post-SIH 2026 changes make it an unfair baseline for a 2025 submission comparison. [Ingestion](https://github.com/namang2/Floatchat-sih2025/blob/25915aa446b33408dd9712a8d21c55e1a6b233b3/ingestion/ingest.py) [Anomaly source](https://github.com/namang2/Floatchat-sih2025/blob/25915aa446b33408dd9712a8d21c55e1a6b233b3/backend_5.0/services/anomalyService.js) |
| [anshul-dying/FloatChat @ `ac493d2`](https://github.com/anshul-dying/FloatChat/tree/ac493d2e38168ef797426d441f7c4b278eb08d4b) | Structured FastAPI/Postgres/Chroma/React scaffold, ingestion and test files, adjusted-first conversion intent, MIT license. | Defaults Docker to a mock LLM and may silently fall back to mock; advanced visualizations synthesize locations/temperature/salinity and random distances; documentation materially exceeds verified behavior. [Conversion](https://github.com/anshul-dying/FloatChat/blob/ac493d2e38168ef797426d441f7c4b278eb08d4b/src/data_ingestion/nc_to_parquet.py) [Synthetic UI](https://github.com/anshul-dying/FloatChat/blob/ac493d2e38168ef797426d441f7c4b278eb08d4b/frontend/src/components/AdvancedVisualizations.jsx) |

**Repeated mistakes to avoid:** (a) embedding every measurement and calling that “RAG”; (b) unrestricted LLM-generated SQL; (c) mixing stale/static/mocked and live data without a visible badge; (d) turning profiles into a flat dataframe while dropping `DATA_MODE`, parameter modes, adjusted errors and provenance; (e) labeling a globe “4D” without a time controller or depth encoding; (f) plotting “time series” with all depth levels joined; (g) equating pressure dbar exactly with metres; (h) claiming heatwaves from a z-score; (i) claiming global/22M scale from one file or row count; and (j) spending the demo on login, voice, 3D decoration and generated narratives rather than a reproducible scientific question.

## 3. Trustworthy data access and QC contract

1. **Canonical source.** Use one of the two synchronized Argo GDACs, and pin a monthly DOI snapshot for judging/reproduction. Argo explicitly says the dataset is updated daily and recommends regular re-sync; monthly snapshots have stable DOI keys. [Argo data access](https://argo.ucsd.edu/data/data-access/) [Argo citation/DOI](https://argo.ucsd.edu/data/acknowledging-argo/)
2. **Discovery before payload.** Mirror/search GDAC profile index files by bounding box, date, WMO, parameters and data mode, then fetch only selected profile/Sprof NetCDF. Do not crawl DAC directories on each user query. The Euro-Argo selection/fleet APIs are public OpenAPI endpoints and are good for metadata/interactive discovery. [Euro-Argo official access page](https://www.euro-argo.eu/Argo-Data-access)
3. **argopy is the safest rapid client.** It supports region, float and profile selections over ERDDAP/GDAC/Argovis. Default `standard` mode merges raw/adjusted values and returns good/probably-good data; `research` retains highest-quality delayed-mode observations and is the defensible mode for sensitive gradient/heat-content work. [argopy fetching guide](https://argopy.readthedocs.io/en/latest/user-guide/fetching-argo-data/index.html) [argopy user modes](https://argopy.readthedocs.io/en/latest/user-guide/fetching-argo-data/user_mode.html)
4. **QC must be first-class.** Preserve original and `*_ADJUSTED`, `*_ADJUSTED_QC`, `*_ADJUSTED_ERROR`, `DATA_MODE`/`PARAMETER_DATA_MODE`, `POSITION_QC`, time QC, WMO, cycle, direction, source file, file update time and DOI snapshot. For research outputs prefer delayed/adjusted fields with QC=1; allow QC=2 only behind an explicit “standard/exploratory” label. Reject 3/4. Argo warns real-time R files can contain drift, delayed D data have expert correction, and adjusted errors must be inspected; it specifically advises rejecting `PRES_ADJUSTED_ERROR > 20 dbar` for bias-sensitive work. [Argo official data FAQ](https://argo.ucsd.edu/data/data-faq/) [Argo ADMT manuals](https://www.argodatamgt.org/Documentation)
5. **NetCDF is not “just CSV.”** It stores dimensions, N-D variables and attributes; Argo's format manual governs profile/B/S-prof structures. Keep raw files immutable and a manifest/checksum. A CSV produced from flattened rows is a convenience export, not a lossless NetCDF round-trip. [NetCDF data model](https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html) [Argo format user manual DOI](https://doi.org/10.13155/29825)
6. **ERDDAP role.** `tabledap` is useful for server-side constraints and CSV/JSON/NetCDF response formats; use encoded, bounded queries, cache responses and retain the request URL as provenance. It is an access layer, not a correctness substitute for Argo QC. [ERDDAP tabledap documentation](https://erddap.github.io/docs/user/tabledap.html)

## 4. Scientifically defensible analytics

### Thermocline

- Work per ascending profile after QC, sort/deduplicate pressure, and require adequate near-surface and vertical coverage. Convert Practical Salinity/in-situ temperature/pressure/position with **TEOS-10** to Absolute Salinity, Conservative Temperature and depth; pressure≈depth is acceptable only as an explicitly labeled display approximation. TEOS-10 provides `SA`, `CT`, density, `N²`, and stability-aware interpolation primitives. [TEOS-10 GSW reference](https://www.teos-10.org/pubs/gsw/html/gsw_contents.html)
- Interpolate conservatively to a regular pressure/depth grid no finer than justified by observations; calculate centered `dCT/dz`. Report the principal thermocline as the depth of maximum **cooling magnitude** (`-dCT/dz`) within a stated window (for example 10–500 m), with top/base as the contiguous region above a declared gradient threshold. Also report local sample spacing and a depth uncertainty of at least half that spacing. Do not invent a result when there is no sustained negative gradient.
- Keep **mixed-layer depth** distinct. A 0.2 °C threshold from a near-surface reference is a standard temperature MLD diagnostic, while gradient/fit methods give a separate estimate; Holte–Talley combines threshold, gradient and fit candidates. [de Boyer Montégut et al. threshold climatology](https://doi.org/10.1029/2003JC002157) [Holte & Talley algorithm](https://doi.org/10.1175/2009JTECHO543.1)

### Salinity gradient / halocline

- Compute `dSA/dz` (g kg⁻¹ m⁻¹) on the same QC-filtered TEOS-10 grid, preserving sign; report maximum absolute gradient and whether salinity rises or falls downward. A cross-section should interpolate **within each profile first**, then interpolate horizontally only where neighboring profiles satisfy distance/time-gap limits; mask unsupported cells rather than paint a smooth ocean. Add observation dots and a coverage layer. Density gradient or `N²` is a useful companion because temperature and salinity can compensate.

### Marine heatwaves and anomalies

- The accepted MHW definition is a **discrete prolonged anomalously warm event**: daily temperature exceeds a seasonally varying 90th-percentile climatological threshold for at least five consecutive days (with documented gap handling); intensity is relative to climatology, not to the current query mean. The reference method uses a multi-decade baseline and day-of-year smoothing. [Hobday et al. 2016](https://doi.org/10.1016/j.pocean.2015.12.014)
- A normal Argo float moves and typically profiles roughly every ten days, so one float cannot establish five consecutive daily conditions at a fixed location. Therefore the honest MVP should call results **“subsurface warm-anomaly candidates”** (co-located/depth-binned departures from a declared baseline), not MHWs. A true MHW feature needs daily gridded temperature plus a ≥30-year climatology and should then use Argo only for subsurface validation. Never substitute global z-scores.

## 5. Recommended architecture for four students

```text
GDAC monthly snapshot + live index delta
  -> immutable NetCDF + manifest (URL, checksum, DOI, fetched_at)
  -> Python/xarray + argopy research/standard policy + TEOS-10
  -> Parquet profile/level cache
  -> PostgreSQL + PostGIS (+ pgvector only for text metadata)
  -> constrained MCP tools / FastAPI
  -> deterministic analytics service
  -> LLM planner and narrator (never calculator/source of facts)
  -> React/Next.js: 2D map + linked Plotly profiles/cross-section + optional WebGL trajectory time slider
```

- **Schema:** `float`, `profile` (WMO+cycle+direction key, time/point geometry/modes/QC/provenance), `level` (raw, best value, adjusted, errors, QC, pressure/depth/SA/CT), `derived_profile` (algorithm+version+parameters+coverage+uncertainty), `source_manifest`, and `document_chunk`. PostGIS GiST on point; B-tree/BRIN on time/WMO/profile; level index on `(profile_id, pressure)`.
- **Storage choices:** PostgreSQL/PostGIS best matches both briefs and nearest-float/time/bbox operations; Parquet is compact/reproducible and DuckDB is an excellent offline read-only fallback; Zarr helps cloud-scale N-D slicing but is unnecessary for the winning slice; SQLite is demo-simple but weak for concurrent geospatial search. Use pgvector rather than a separate vector service unless scale proves otherwise.
- **Query safety:** expose typed tools such as `find_profiles(bbox,time,params,qc_mode)`, `nearest_floats(point,k,time)`, `get_profile(wmo,cycle)`, `compare_profiles(ids)`, and `derive_cross_section(...)`. Validate units/ranges, cap rows/time, use read-only credentials and parameterized SQL. The model selects tools and explains returned JSON; it never emits executable arbitrary SQL. Return `answer`, `data`, `chart_spec`, `provenance`, `qc_summary`, `assumptions`, and `warnings`.
- **Visualization:** use a fast 2D WebGL map (deck.gl/MapLibre) with clustering and time slider; linked depth-down profiles and section plots are more scientifically useful than a decorative globe. If the ORION 4D criterion demands 3D, render sampled trajectory `(lon,lat,depth,time)` after the 2D path works, with LOD/decimation and a visible count of rendered vs total points.
- **Team split:** (1) ingestion/QC/provenance, (2) database/MCP/API/security, (3) deterministic ocean analytics and validation fixtures, (4) linked UI/visualization/demo; all share the gold-query test set and final integration.

## 6. Minimum winning vertical slice and differentiation

**One uninterrupted demo:** ask “Compare reliable temperature and salinity structure for floats near 10°N, 70°E in March 2023.” The planner shows parsed bbox/time/QC mode; map returns real profiles; selecting two opens QC-aware CT/SA profiles; “derive section” displays observation-backed thermocline/halocline with gaps masked; the answer cites WMO/cycles, data modes, retained/rejected counts, algorithm/version and monthly DOI; CSV and a faithful selected NetCDF subset download; disabling network repeats from cache with the same manifest.

**Differentiate without copying:**

- “Scientific receipt” on every answer (source URL/DOI, snapshot, query/tool call, units, QC/mode, row/profile counts, derived-method parameters).
- Side-by-side **raw vs best-adjusted** toggle that visibly demonstrates why QC changes a conclusion.
- Coverage/uncertainty visualization and explicit “insufficient evidence,” instead of hallucinated smooth fields.
- Deterministic replay links and an offline judge mode.
- A query-evaluation harness and latency dashboard, not generic claims.
- Accessibility: 2D fallback, keyboard filters, colorblind palette, depth axis downward, downloadable underlying points.

Do not copy repository branding, layouts, prompts, screenshots, generated datasets or code. Ideas and public interfaces are not ownership-free implementations; independently derive your schema/tool contracts from official documentation and keep a design log showing that provenance.

## 7. Measurable acceptance benchmarks

| Dimension | Minimum target and test |
| --- | --- |
| Ingestion correctness | 100% of fixture profiles retain WMO/cycle/direction/time/position/mode/QC/error/source; best-value choice matches a hand-audited 20-profile fixture; idempotent re-run produces zero duplicate keys. |
| QC | Zero QC 3/4 levels in research outputs; response reports input/retained/rejected counts; 100% outputs identify standard vs research policy. |
| Query semantics | ≥27/30 curated prompts choose the right typed tool and filters; exact result agreement for 15 deterministic aggregation/nearest/profile cases; 100% refuse mutation/unbounded/raw-SQL injection cases. |
| Grounding | 100% numerical claims trace to returned fields; 100% answers include WMO/cycle and source manifest; zero invented units in gold set. |
| Science | Thermocline and salinity-gradient depth within one native vertical interval of hand-calculated synthetic/reference casts; no result when coverage rules fail; MHW label blocked unless daily/climatology criteria are present. |
| Latency | Warm-cache p95 <1 s for metadata/nearest queries and <3 s end-to-end excluding LLM; cold external fetch clearly separated; test on stated hardware and dataset size. |
| Visualization | 100k points interactive at ≥30 FPS on declared laptop; initial clustered map <2 s warm; LOD preserves selected profiles exactly. This directly answers ORION's stated rendering criterion. |
| Reliability | Entire vertical slice works with network disabled after priming; upstream timeout returns stale timestamp/source warning, never mock scientific values. |
| Export | Exported row count/units/QC/provenance match on-screen selection; NetCDF subset opens and retains relevant variable attributes. |

## 8. Risks, licensing and delivery controls

- **Scientific/reputational:** silent raw/adjusted mixing, BGC parameters with different pressure axes, moving-platform “time series,” sparse cross-sections and false heatwave claims. Mitigate with a written data contract, method versioning and insufficiency states.
- **Operational:** ERDDAP/GDAC latency, rate limits and a venue network outage. Pin/cache a modest Indian Ocean snapshot, add timeouts/retries, never silently generate fallback data.
- **LLM/security:** prompt injection in metadata, data exfiltration, destructive/expensive SQL, API cost/rate limits. Use typed MCP tools, read-only DB, statement timeout, row caps, allowlisted fields and deterministic non-LLM fallback filters.
- **Scope:** BGC, forecasting, voice, auth, Cesium/3D globe and multi-cloud are attractive traps. Ship core T/S first; one BGC parameter only after its official QC cookbook is implemented.
- **Data credit:** cite Argo as `Argo (2000). Argo float data and metadata from Global Data Assembly Centre (Argo GDAC). SEANOE. https://doi.org/10.17882/42182` and add the monthly snapshot key for reproducibility. [Official acknowledgment](https://argo.ucsd.edu/data/acknowledging-argo/)
- **Code licensing/plagiarism:** MIT permits reuse with copyright/license notice, but only ro-lex404 and anshul had an obvious MIT license file among the audited roots; absent license means **no permission to copy** by default. vishal's README statement is not a substitute for a present license text. Preserve notices for every reused dependency/snippet, inventory frontend assets/models/fonts, scan secrets and licenses, and comply with ORION's explicit plagiarism screening. [ORION timeline/evaluation notice](https://orion.sathyabama.ac.in/#timeline)

## Sources

### Kept

- [ORION 1.0 official site](https://orion.sathyabama.ac.in/#challenges) — primary current challenge, deliverables and evaluation criteria.
- [SIH 25040 transcription](https://github.com/iamNVN/SIH-ARGOFloat/blob/156731264ecd30fb93d755d93174ea356dc154d5/README.md) — requested public implementation README preserving the original problem text; the SIH 2025 live table currently no longer exposes the entry.
- [Argo Data Management documentation](https://www.argodatamgt.org/Documentation) — canonical format/QC manuals and cookbooks.
- [Argo data FAQ](https://argo.ucsd.edu/data/data-faq/) — authoritative raw/delayed/adjusted/QC guidance.
- [argopy documentation](https://argopy.readthedocs.io/en/latest/user-guide/fetching-argo-data/index.html) — supported sources/selections and processing modes.
- [Euro-Argo data access](https://www.euro-argo.eu/Argo-Data-access) — official selection/fleet tools and public APIs.
- [ERDDAP tabledap](https://erddap.github.io/docs/user/tabledap.html) and [NetCDF model](https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html) — protocol and file-model constraints.
- Requested repositories and two additional substantial implementations, all pinned in the audit table — direct code evidence.
- [TEOS-10 GSW](https://www.teos-10.org/pubs/gsw/html/gsw_contents.html), [de Boyer Montégut 2004](https://doi.org/10.1029/2003JC002157), [Holte & Talley 2009](https://doi.org/10.1175/2009JTECHO543.1), and [Hobday et al. 2016](https://doi.org/10.1016/j.pocean.2015.12.014) — primary standard/method papers needed to avoid scientifically false feature labels.

### Dropped

- Search-result snippets, blogs, AI-generated repository summaries, vendor comparison pages and tutorial articles — not primary evidence.
- Repository screenshots/videos as proof of internals — useful presentation evidence but not implementation or correctness evidence.
- README scale/performance assertions without a script, fixture or captured benchmark — reported above only as claims, not facts.

## Gaps

- The live SIH 2025 problem table is now empty/retired; exact SIH organization metadata beyond the preserved public README could not be independently recovered from the official site. Obtain the archived official PS PDF/export from organizers if formal attribution matters.
- ORION's modal names “FastFloat Engine,” “ARGO NetCDF API,” Copernicus and NOAA but publishes no interface specification, baseline dataset, scoring weights or benchmark harness. Ask organizers whether these are mandatory, and what “forecast” means, before committing architecture.
- No official ORION test dataset or exact 4D definition was published. Benchmark targets above are recommended engineering acceptance thresholds, not organizer-guaranteed cutoffs.
- Full reproducibility of repository claims would require environment/API credentials and database dumps; this audit establishes source presence and obvious behavior, not successful deployment of every project.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Created only the requested research dossier at /home/wk/floatchat-research.md; no application code or scaffold was produced."
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "Dossier includes primary-source citations, commit-pinned source audits, explicit confidence/gaps, architecture, methods, benchmarks, risks, and source retention rationale."
    }
  ],
  "changedFiles": [
    "/home/wk/floatchat-research.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "git clone --depth 1 for eight public FloatChat/SIH repositories; grep/sed source audits",
      "result": "passed",
      "summary": "Inspected pinned revisions, READMEs, source trees, mock/random/QC/adjusted-data usage, and license presence."
    },
    {
      "command": "curl official ORION, Argo ADMT/UCSD, Euro-Argo, argopy, ERDDAP, NetCDF and method sources",
      "result": "passed",
      "summary": "Verified primary pages and extracted challenge, QC, access, format and scientific-method requirements."
    },
    {
      "command": "git status --porcelain in /home/wk",
      "result": "passed",
      "summary": "No repository/staged files were present."
    }
  ],
  "validationOutput": [
    "ORION source identifies ORION-PS-01 and its four key features, deliverables and evaluation focus.",
    "Audited repository revisions are commit-pinned in the dossier.",
    "Official Argo guidance supports delayed adjusted data, QC filtering, adjusted-error checks and DOI snapshots.",
    "Artifact path is exactly /home/wk/floatchat-research.md."
  ],
  "residualRisks": [
    "The retired official SIH 2025 table prevented direct recovery of problem 25040; lineage relies on a commit-pinned public submission README plus strong textual chronology.",
    "Repository systems were source-audited but not all were fully deployed because external credentials/databases are unavailable.",
    "ORION has not published scoring weights, an official dataset, or a definition of FastFloat Engine/4D."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added one Markdown research dossier; no code changes.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Independent reviewer should spot-check the ORION modal/chunk content and at least one pinned source link because the official challenge page is client-rendered."
}
```
