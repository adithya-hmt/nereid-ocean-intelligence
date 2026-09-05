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
