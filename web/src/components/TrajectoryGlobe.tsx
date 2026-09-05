'use client'

import { Canvas, useThree } from '@react-three/fiber'
import { Component, type ErrorInfo, type ReactNode, useEffect, useMemo, useState } from 'react'

import { buildTrajectoryBuffers, type TrajectoryRow } from '../lib/geometry'
import { TimeController } from './TimeController'
import { TrajectoryFallback } from './TrajectoryFallback'

type Props = { rows: readonly TrajectoryRow[]; benchmark?: boolean }

type BoundaryProps = { children: ReactNode; onError: () => void }
type BoundaryState = { failed: boolean }
class WebglBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false }
  static getDerivedStateFromError(): BoundaryState { return { failed: true } }
  componentDidCatch(_: Error, __: ErrorInfo) { this.props.onError() }
  render() { return this.state.failed ? null : this.props.children }
}

function PointCloud({ rows, exaggeration }: { rows: readonly TrajectoryRow[]; exaggeration: number }) {
  const invalidate = useThree((state) => state.invalidate)
  const buffers = useMemo(() => buildTrajectoryBuffers(rows, exaggeration), [rows, exaggeration])
  useEffect(() => { invalidate() }, [buffers, invalidate])
  return <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[buffers.positions, 3]} /><bufferAttribute attach="attributes-color" args={[buffers.colors, 3]} /></bufferGeometry><pointsMaterial vertexColors size={0.012} sizeAttenuation /></points>
}

export function TrajectoryGlobe({ rows, benchmark = false }: Props) {
  const [cutoff, setCutoff] = useState(Math.max(rows.length - 1, 0))
  const [exaggeration, setExaggeration] = useState(20)
  const [force2d, setForce2d] = useState(false)
  const [webglFailed, setWebglFailed] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const [ready, setReady] = useState(false)
  const timestamps = useMemo(() => rows.map((row) => row.timestamp), [rows])
  const visibleRows = useMemo(() => rows.slice(0, cutoff + 1), [rows, cutoff])
  const fallback = force2d || webglFailed || reducedMotion || (typeof window !== 'undefined' && typeof ResizeObserver === 'undefined')

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReducedMotion(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return <section className="trajectory-view" aria-labelledby="trajectory-heading" data-render-ready={ready ? 'true' : undefined}>
    <div className="section-title"><h2 id="trajectory-heading">Float trajectories through space and time</h2><button type="button" className="text-button" onClick={() => setForce2d((value) => !value)}>{force2d ? 'Use WebGL globe' : 'Use 2D fallback'}</button></div>
    {benchmark && <p className="benchmark-label">Benchmark only — synthetic rows are never scientific results.</p>}
    <div className="trajectory-controls"><TimeController timestamps={timestamps} cutoff={cutoff} onChange={setCutoff} /><label>Vertical exaggeration (radial depth ×)
      <input aria-label="Vertical exaggeration" type="range" min="0" max="100" value={exaggeration} onChange={(event) => setExaggeration(Number(event.target.value))} /><output>{exaggeration}×</output>
    </label></div>
    {fallback ? <TrajectoryFallback rows={visibleRows} label={reducedMotion ? '2D longitude/latitude fallback (reduced motion)' : webglFailed ? '2D longitude/latitude fallback (WebGL unavailable)' : undefined} /> : <WebglBoundary onError={() => setWebglFailed(true)}><div className="globe-canvas"><Canvas frameloop="demand" camera={{ position: [0, 0, 2.6], fov: 45 }} onCreated={({ gl }) => { gl.setClearColor('#f4f7f4'); setReady(true) }}><ambientLight intensity={1} /><PointCloud rows={visibleRows} exaggeration={exaggeration} /></Canvas></div></WebglBoundary>}
    <p className="trajectory-readout">Longitude/latitude/depth use source coordinates; time cutoff: {timestamps[cutoff] ? new Date(timestamps[cutoff]).toISOString() : 'none'}; rendered {visibleRows.length.toLocaleString()} of {rows.length.toLocaleString()} points; vertical exaggeration {exaggeration}×.</p>
  </section>
}
