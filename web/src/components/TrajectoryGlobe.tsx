'use client'

import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Component, type ErrorInfo, type ReactNode, useEffect, useMemo, useRef, useState } from 'react'

import type { TrajectoryRow } from '../lib/geometry'
import { createTrajectoryGeometry, updateTrajectoryGeometry } from '../lib/point-cloud'
import { rowsAtOrBefore, sortedUniqueTimestamps } from '../lib/trajectory'
import { hasWebGLSupport } from '../lib/webgl'
import { TimeController } from './TimeController'
import { TrajectoryFallback } from './TrajectoryFallback'

type BenchmarkMetrics = { initializationMs?: number; r3fFps?: number; browser?: string; hardware?: string; vendor?: string; renderer?: string; softwareRasterizer?: boolean; probeOverheadMs?: number; frameIntervalMs?: number; invalidations?: number }
type Props = { rows: readonly TrajectoryRow[]; benchmark?: boolean; drawPoints?: boolean }
type BoundaryProps = { children: ReactNode; onError: () => void }
type BoundaryState = { failed: boolean }

class WebglBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false }
  static getDerivedStateFromError(): BoundaryState { return { failed: true } }
  componentDidCatch(_: Error, __: ErrorInfo) { this.props.onError() }
  render() { return this.state.failed ? null : this.props.children }
}

function PointCloud({ rows, capacity, exaggeration }: { rows: readonly TrajectoryRow[]; capacity: number; exaggeration: number }) {
  const invalidate = useThree((state) => state.invalidate)
  const geometry = useMemo(() => createTrajectoryGeometry(capacity), [capacity])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => { updateTrajectoryGeometry(geometry, rows, exaggeration); invalidate() }, [geometry, rows, exaggeration, invalidate])
  return <points><primitive object={geometry} attach="geometry" dispose={null} /><pointsMaterial vertexColors size={0.003} sizeAttenuation /></points>
}

function FrameProbe({ benchmark, startedAt, onFirstFrame, onComplete }: { benchmark: boolean; startedAt: { current: number }; onFirstFrame: (initializationMs: number) => void; onComplete: (fps: number, probeOverheadMs: number, frameIntervalMs: number, invalidations: number) => void }) {
  const invalidate = useThree((state) => state.invalidate)
  const frameState = useRef({ seen: false, sampleStartedAt: 0, previousFrameAt: 0, frames: 0, complete: false, probeOverheadMs: 0, frameIntervalsMs: 0, invalidations: 0 })
  useFrame(() => {
    const callbackStartedAt = performance.now()
    const state = frameState.current
    const now = callbackStartedAt
    if (!state.seen) {
      state.seen = true
      state.sampleStartedAt = now
      state.previousFrameAt = now
      onFirstFrame(now - startedAt.current)
    }
    if (!benchmark || state.complete) return
    state.frames += 1
    state.frameIntervalsMs += now - state.previousFrameAt
    state.previousFrameAt = now
    const elapsed = now - state.sampleStartedAt
    if (elapsed >= 5000) {
      state.complete = true
      state.probeOverheadMs += performance.now() - callbackStartedAt
      onComplete(state.frames / (elapsed / 1000), state.probeOverheadMs / state.frames, state.frameIntervalsMs / state.frames, state.invalidations)
      return
    }
    state.invalidations += 1
    invalidate()
    state.probeOverheadMs += performance.now() - callbackStartedAt
  })
  return null
}

const browserDetails = () => typeof navigator === 'undefined' ? {} : {
  browser: navigator.userAgent,
  hardware: `hardwareConcurrency=${navigator.hardwareConcurrency}; deviceMemory=${(navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 'unavailable'} GB`,
}

export function TrajectoryGlobe({ rows, benchmark = false, drawPoints = true }: Props) {
  const timestamps = useMemo(() => sortedUniqueTimestamps(rows), [rows])
  const [cutoff, setCutoff] = useState(Math.max(timestamps.length - 1, 0))
  const [exaggeration, setExaggeration] = useState(20)
  const [force2d, setForce2d] = useState(false)
  const [webglFailed, setWebglFailed] = useState(() => typeof window !== 'undefined' && (typeof ResizeObserver === 'undefined' || !hasWebGLSupport()))
  const [reducedMotion, setReducedMotion] = useState(false)
  const [ready, setReady] = useState(false)
  const [metrics, setMetrics] = useState<BenchmarkMetrics>({})
  const startedAt = useRef(0)
  const selectedTimestamp = timestamps[Math.min(cutoff, Math.max(timestamps.length - 1, 0))]
  const visibleRows = useMemo(() => selectedTimestamp ? rowsAtOrBefore(rows, selectedTimestamp) : [], [rows, selectedTimestamp])
  const fallback = force2d || webglFailed || reducedMotion
  const depthRange = visibleRows.length ? [Math.min(...visibleRows.map((row) => row.depth_m)), Math.max(...visibleRows.map((row) => row.depth_m))] : [0, 0]
  const longitudeRange = visibleRows.length ? [Math.min(...visibleRows.map((row) => row.longitude)), Math.max(...visibleRows.map((row) => row.longitude))] : [0, 0]
  const latitudeRange = visibleRows.length ? [Math.min(...visibleRows.map((row) => row.latitude)), Math.max(...visibleRows.map((row) => row.latitude))] : [0, 0]

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReducedMotion(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  const recordFirstFrame = (initializationMs: number) => { setReady(true); setMetrics((current) => ({ ...current, ...browserDetails(), initializationMs })) }
  const recordComplete = (r3fFps: number, probeOverheadMs: number, frameIntervalMs: number, invalidations: number) => setMetrics((current) => ({ ...current, r3fFps, probeOverheadMs, frameIntervalMs, invalidations }))
  return <section className="trajectory-view" aria-labelledby="trajectory-heading" data-render-ready={ready ? 'true' : undefined} data-render-benchmark-complete={metrics.r3fFps ? 'true' : undefined}>
    <div className="section-title"><h2 id="trajectory-heading">Float trajectories through space and time</h2><button type="button" className="text-button" onClick={() => setForce2d((value) => !value)}>{force2d ? 'Use WebGL globe' : 'Use 2D fallback'}</button></div>
    {benchmark && <aside className="benchmark-panel" aria-label="Benchmark-only rendering measurements"><p className="benchmark-label">Benchmark only — synthetic rows are never scientific results.</p><dl><dt>Declared browser</dt><dd>Playwright benchmark runner</dd><dt>Declared hardware</dt><dd>Browser-reported capabilities, captured separately below</dd><dt>Measured initialization</dt><dd data-benchmark-initialization>{metrics.initializationMs === undefined ? 'Pending first R3F frame' : `${metrics.initializationMs.toFixed(3)} ms`}</dd><dt>Measured R3F FPS</dt><dd data-benchmark-r3f-fps>{metrics.r3fFps === undefined ? 'Sampling five seconds of R3F frames' : metrics.r3fFps.toFixed(3)}</dd><dt>Measured browser</dt><dd data-benchmark-browser>{metrics.browser ?? 'Pending'}</dd><dt>Measured hardware</dt><dd data-benchmark-hardware>{metrics.hardware ?? 'Pending'}</dd><dt>WebGL vendor / renderer</dt><dd data-benchmark-renderer>{metrics.vendor && metrics.renderer ? `${metrics.vendor} / ${metrics.renderer}` : 'Pending'}</dd><dt>Probe overhead / frame interval</dt><dd data-benchmark-probe>{metrics.probeOverheadMs === undefined ? 'Sampling' : `${metrics.probeOverheadMs.toFixed(3)} ms / ${metrics.frameIntervalMs?.toFixed(3)} ms; invalidations=${metrics.invalidations}`}</dd></dl></aside>}
    <div className="trajectory-controls"><TimeController timestamps={timestamps} cutoff={cutoff} onChange={setCutoff} /><label>Vertical exaggeration (radial depth ×)<input aria-label="Vertical exaggeration" type="range" min="0" max="100" value={exaggeration} onChange={(event) => setExaggeration(Number(event.target.value))} /><output>{exaggeration}×</output></label></div>
    {fallback ? <TrajectoryFallback rows={visibleRows} label={reducedMotion ? '2D longitude/latitude fallback (reduced motion)' : webglFailed ? '2D longitude/latitude fallback (WebGL unavailable)' : undefined} /> : <WebglBoundary onError={() => setWebglFailed(true)}><div className="globe-canvas"><Canvas frameloop="demand" camera={{ position: [0, 0, 2.6], fov: 45 }} onCreated={({ gl }) => { startedAt.current = performance.now(); gl.setClearColor('#f4f7f4'); const context = gl.getContext(); const debug = context.getExtension('WEBGL_debug_renderer_info'); const vendor = debug ? context.getParameter(debug.UNMASKED_VENDOR_WEBGL) : context.getParameter(context.VENDOR); const renderer = debug ? context.getParameter(debug.UNMASKED_RENDERER_WEBGL) : context.getParameter(context.RENDERER); setMetrics((current) => ({ ...current, vendor, renderer, softwareRasterizer: /swiftshader|software|llvmpipe/i.test(renderer) })) }}><ambientLight intensity={1} />{drawPoints && <PointCloud rows={visibleRows} capacity={rows.length} exaggeration={exaggeration} />}<FrameProbe benchmark={benchmark} startedAt={startedAt} onFirstFrame={recordFirstFrame} onComplete={recordComplete} /></Canvas></div></WebglBoundary>}
    <p className="trajectory-readout">Longitude {longitudeRange[0].toFixed(3)}° to {longitudeRange[1].toFixed(3)}°; latitude {latitudeRange[0].toFixed(3)}° to {latitudeRange[1].toFixed(3)}°; depth {depthRange[0].toFixed(1)} to {depthRange[1].toFixed(1)} m; time cutoff: {selectedTimestamp ?? 'none'}; rendered {visibleRows.length.toLocaleString()} of {rows.length.toLocaleString()} points; vertical exaggeration {exaggeration}×.</p>
  </section>
}
