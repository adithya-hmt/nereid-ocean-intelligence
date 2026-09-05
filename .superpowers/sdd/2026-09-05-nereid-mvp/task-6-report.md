# Task 6 report

Implemented a typed ARGO 4D trajectory renderer: deterministic geographic projection, typed point/color buffers, a demand-framed React Three Fiber point cloud, time cutoff, labeled radial-depth exaggeration, and source-coordinate readouts. The renderer provides a keyboard-operable SVG longitude/latitude fallback for reduced motion, WebGL failure, and explicit user selection. Benchmark rows are deterministic synthetic data and visibly labeled benchmark-only; they do not enter `ResultEnvelope` scientific results.

## Validation

- `pnpm --dir web test --run`: passed (11 tests).
- `pnpm --dir web lint`: passed.
- `pnpm --dir web build`: passed.
- `pnpm --dir web exec playwright test e2e/rendering.spec.ts`: passed after the benchmark URL-host fix.

## Benchmark evidence

The evidence is intentionally benchmark-only and is kept separate from scientific result envelopes. `docs/evidence/rendering.json` now records measured initialization time and five-second browser FPS, alongside distinct declared browser/hardware context.

## Benchmark debugging follow-up

### Root cause

The Playwright configuration used `127.0.0.1` while Next dev identified itself as `localhost`. Captured browser output showed repeated failed HMR WebSocket handshakes and Next reported blocked cross-origin dev requests. The workspace did receive `?benchmark=100000` and generated/rendered all 100,000 rows, but the WebGL canvas never reached its readiness marker under that mismatched dev origin. A direct trace at `localhost` showed one canvas and one readiness marker after three seconds, with no fallback.

### Red → green

- **Red:** the added page regression initially proved the route did not forward the `benchmark=100000` query through the static client boundary; it timed out because the fallback SVG attempted to render 100,000 circles in jsdom.
- **Fix:** route query parsing now occurs in the server page and passes a typed `benchmark` prop into the workspace; the regression mocks the globe and verifies benchmark forwarding. Playwright now uses `localhost` consistently for `baseURL` and `webServer` readiness, matching Next dev's origin.
- **Green:** page regression passes and the rendering benchmark passes, producing measured evidence: initialization `2135.244563 ms`, five-second FPS `60.01994017946162` on the declared Playwright Chromium environment.

### Commands

- `pnpm --dir web test --run src/app/page.test.tsx`
- `pnpm --dir web exec playwright test e2e/rendering.spec.ts`
- `pnpm --dir web test --run`
- `pnpm --dir web lint`
- `pnpm --dir web build`

## Fix round 1: benchmark and trajectory integrity

### Findings addressed

1. The prior browser `requestAnimationFrame` counter and `Canvas.onCreated` marker were not evidence of actual R3F rendering. The benchmark now uses an in-canvas `useFrame` probe. Its first callback records initialization and marks render-ready only after a real R3F frame. In benchmark mode, it explicitly calls `invalidate()` from that callback while retaining normal `frameloop="demand"`, counts actual R3F frames for five seconds, then exposes the resulting FPS.
2. Time cutoff now derives sorted, unique parsed timestamps and filters immutable source rows by `timestamp <= cutoff`; same-timestamp profile depths are therefore selected together even when source rows are unsorted. `trajectory.test.ts` covers both cases.
3. Normal WebGL readout now exposes accessible longitude, latitude, and depth min/max ranges, in addition to cutoff time, rendered/total counts, and exaggeration.
4. Benchmark mode contains a visible accessible panel separating declared runner browser/hardware from measured initialization, actual R3F FPS, browser, and hardware. Playwright reads those live panel values only after benchmark completion and writes them to evidence.
5. WebGL support is preflighted before Canvas mounting; canvas-capable documents with unavailable WebGL route directly to the SVG fallback. `webgl.test.ts` covers this browser capability boundary.

### Evidence and result

- Red: actual R3F measurement exposed the earlier RAF claim as invalid. With the five-second in-canvas probe, this HeadlessChrome environment measured `10.984` R3F FPS rather than the prior browser RAF value near 60.
- Mitigation: visible point size was reduced from `0.012` to `0.003`. The truthful post-mitigation value remains below the design target, so it is not represented as meeting 30 FPS.
- Green: `pnpm --dir web exec playwright test e2e/rendering.spec.ts` passes and generated `docs/evidence/rendering.json` from the live benchmark panel: initialization `1.3 ms`, actual R3F FPS `10.984`, browser and hardware separately recorded.
- Commands: `pnpm --dir web test --run`; `pnpm --dir web lint`; `pnpm --dir web build`; `pnpm --dir web exec playwright test e2e/rendering.spec.ts`.

## Fix round 2: actual-frame performance diagnosis

### Instrumentation and root cause

The benchmark now runs two comparable five-second `useFrame` samples under the same Playwright Chromium session: an empty Canvas with no point draw and the 100,000-point cloud. The live benchmark panel and checked-in evidence record vendor/renderer, sample frame interval, probe callback overhead, and scheduled demand invalidations.

The evidence identifies one root cause: **the 100,000-point draw on the software SwiftShader renderer is the bottleneck, not Canvas, R3F frame scheduling, or the probe.** The empty Canvas measured `60.264` actual R3F FPS (`16.594 ms` frame interval), while the point cloud measured `11.269` FPS (`88.737 ms` interval). Both report `ANGLE ... SwiftShader Device (Subzero) ... SwiftShader driver`. Probe work averaged only `0.004 ms` empty and `0.007 ms` with points, and each sample scheduled the expected demand invalidations (301 and 56 respectively). Because empty Canvas is above 30, a GPU-launch configuration would not diagnose this point-rendering gap and was not used to tune the number.

### Optimization and resource proof

The point cloud now creates one capacity-sized `BufferGeometry` and two `DynamicDrawUsage` attributes per source dataset, then updates their existing typed arrays and `drawRange` in place for cutoff/exaggeration changes. The geometry is disposed only when its capacity resource is replaced/unmounted. `point-cloud.test.ts` proves that cutoff updates preserve position/color attribute identity while changing draw range. This is the smallest applicable optimization; remeasurement improved the cloud from `10.984` to `11.269` actual FPS, but cannot reach 30 under SwiftShader.

### Commands

- `pnpm --dir web test --run src/lib/point-cloud.test.ts`
- `pnpm --dir web exec playwright test e2e/rendering.spec.ts`
- `pnpm --dir web test --run`
- `pnpm --dir web lint`
- `pnpm --dir web build`

## Fix round 3: bounded hardware-launch hypothesis

### Hypothesis and result

The sole launch-only hypothesis was a headed Playwright launch on the host display using `/usr/bin/chromium`; no application or renderer code was changed before this test. It was confirmed: the same 100,000-point cloud moved from SwiftShader to `ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (WHL GT2), OpenGL ES 3.2)` and measured `57.718` actual R3F FPS in the direct trace. The reproducible configured run then measured `59.389` actual R3F FPS over five seconds (empty Canvas `60.466` FPS), exceeding the 30 FPS target. Probe overhead remained negligible (`0.006 ms`) and the sample scheduled 297 demand invalidations.

### Reproducibility

`web/playwright.config.ts` keeps the default Playwright workflow headless and bundled. Set `NEREID_BENCHMARK_GPU=1` to opt into the declared benchmark mode: headed system Chromium at `/usr/bin/chromium` using `DISPLAY=:0` / `WAYLAND_DISPLAY=wayland-1`. The live evidence records this exact mode, executable, measured browser/hardware, and Intel renderer; it is generated by `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts`.

The shader-material hypothesis was not performed because the first bounded hypothesis met the actual-R3F target without altering draw semantics, downsampling, or weakening measurement.

### Commands

- headed trace: Playwright `chromium.launch({ headless: false, executablePath: '/usr/bin/chromium' })`
- `NEREID_BENCHMARK_GPU=1 pnpm --dir web exec playwright test e2e/rendering.spec.ts`
- `pnpm --dir web test --run`
- `pnpm --dir web lint`
- `pnpm --dir web build`
