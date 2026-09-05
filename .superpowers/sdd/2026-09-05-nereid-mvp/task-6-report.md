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
