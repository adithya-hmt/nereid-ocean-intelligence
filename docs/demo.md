# Nereid hackathon demo

## 90-second flow

**0:00 — Problem**

“ARGO contains extraordinary ocean observations, but answering a question defensibly still requires finding the right profile representation, applying QC correctly, computing TEOS-10 quantities, and preserving evidence.”

**0:15 — Run the pinned investigation**

Open `http://localhost:3100`, choose **Use March 2023 example**, then **Run investigation**.

“This is a fully offline replay of official GDAC data—not synthetic measurements. The exact source files, DOI, timestamps, and hashes are committed.”

**0:30 — Show linked evidence**

Point out the 4D trajectory, separate native profile panels, and canonical thermocline/salinity-gradient metrics.

“Nereid preserves WMO, cycle, ascent/descent direction, and every source representation. Research mode uses adjusted QC 1; QC 3 and 4 never enter scientific output.”

**0:50 — Derive a section**

Keep two exact representations selected and choose **Derive section from selected representations**.

“The section is chronological and parameter-faithful. It refuses oversized work and visibly masks unsupported vertical, time, or distance gaps instead of smoothing through them.”

**1:10 — Prove reproducibility**

Show the query and derived-section receipts, then download the evidence ZIP.

“The ZIP contains selected rows, provenance, the validated query plan, QC counts, metrics, algorithms, assumptions, warnings, TEOS-10 methods, and units. Its content is deterministic across input order and Python hash seeds.”

**1:25 — Close**

“An optional Azure model can translate language into this typed plan—but it cannot write SQL, run analytics, or invent a scientific claim. Without credentials, every explicit workflow still works.”

## Judge questions

### Is this real ARGO data?

Yes. `data/snapshots/indian-ocean-2023-03/manifest.jsonl` cites official GDAC URLs, DOI `10.17882/42182`, fetch timestamps, and SHA-256 checksums. Raw NetCDF files are included for replay.

### What makes the calculations trustworthy?

Scientific values pass pressure and parameter-specific adjusted QC. Absolute Salinity uses `SA_from_SP`; Conservative Temperature uses `CT_from_t`; depth uses `z_from_p`. Raw fallbacks with rejected raw QC are quarantined.

### What does AI control?

Only construction of an allow-listed, locally validated `QueryPlan`. It cannot generate SQL, calculations, measurements, conclusions, or evidence.

### Why does it work offline?

The normalized snapshot is committed locally, DuckDB queries Parquet in-process, and the winning Playwright flow blocks every non-loopback request.

### What remains externally blocked?

The live Azure planner score cannot be measured without the four Azure environment variables. The local evaluator exits 2 and reports that block instead of fabricating a score.

## Recovery

- API health: `curl http://127.0.0.1:8000/health`
- Restart both services: stop `pnpm dev`, then run it again from the repository root.
- AI unavailable: continue with explicit controls; this is expected behavior.
- WebGL unavailable: Nereid uses its accessible 2D trajectory fallback.
