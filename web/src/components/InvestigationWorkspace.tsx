'use client'

import { useMemo, useRef, useState } from 'react'
import { ApiError, executeQuery } from '../lib/api'
import { createBenchmarkRows } from '../lib/benchmark-data'
import { isTrajectoryRow } from '../lib/geometry'
import type { QueryPlan, ResultEnvelope } from '../lib/types'
import { CrossSectionPlot } from './CrossSectionPlot'
import { ProfilePlot } from './ProfilePlot'
import { QueryControls } from './QueryControls'
import { QueryPlanPanel } from './QueryPlanPanel'
import { ScientificReceipt } from './ScientificReceipt'
import { TrajectoryGlobe } from './TrajectoryGlobe'

const winningPlan: QueryPlan = { operation: 'find_profiles', bbox: [60, 0, 80, 20], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP', 'PSAL'], qc_mode: 'research', row_limit: 10000 }

type Props = { initialResult?: ResultEnvelope; benchmark?: boolean; emptyBenchmark?: boolean }

export function InvestigationWorkspace({ initialResult, benchmark = false, emptyBenchmark = false }: Props) {
  const benchmarkRows = useMemo(() => benchmark && !emptyBenchmark ? createBenchmarkRows(100_000) : [], [benchmark, emptyBenchmark])
  const [plan, setPlan] = useState<QueryPlan>(winningPlan)
  const [result, setResult] = useState<ResultEnvelope | undefined>(initialResult)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const request = useRef<AbortController | undefined>(undefined)

  const submit = async () => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true)
    setError(undefined)
    try {
      const nextResult = await executeQuery(plan, controller.signal)
      if (request.current === controller) setResult(nextResult)
    } catch (caught) {
      if (request.current === controller && !(caught instanceof DOMException && caught.name === 'AbortError')) setError(caught instanceof ApiError ? `${caught.status}: ${caught.message}` : 'The investigation could not be updated. Check the snapshot and try again.')
    } finally {
      if (request.current === controller) setLoading(false)
    }
  }

  const trajectoryRows = result?.data.filter(isTrajectoryRow) ?? []
  return <main className="workspace"><header className="workspace-header"><h1>Nereid Ocean Investigation</h1><p>Traceable ARGO evidence for a bounded question near 10°N, 70°E.</p></header>{benchmark ? <><TrajectoryGlobe rows={benchmarkRows} benchmark drawPoints={!emptyBenchmark} /><p className="benchmark-label">Declared browser and hardware are recorded separately from measured values in the rendering benchmark evidence.</p></> : <><QueryControls plan={plan} loading={loading} onChange={setPlan} onSubmit={submit} onExample={() => setPlan(winningPlan)} /><QueryPlanPanel plan={plan} />{error && <p className="status error" role="alert">{error}</p>}{result ? <><section className="visualization" aria-labelledby="visualization-heading"><h2 id="visualization-heading">Investigation view</h2>{trajectoryRows.length ? <TrajectoryGlobe key={`${trajectoryRows.length}-${trajectoryRows[0].timestamp}`} rows={trajectoryRows} /> : result.data.length ? <p className="status empty">The returned observations have no complete longitude, latitude, depth, and time coordinates for a truthful trajectory.</p> : <p className="status empty">{result.warnings[0] ?? 'No observations are available for this bounded request.'}</p>}</section><ProfilePlot result={result} /><CrossSectionPlot result={result} /><ScientificReceipt result={result} /></> : <section className="visualization empty" aria-live="polite"><h2>Investigation view</h2><p>Run the bounded query to inspect source-faithful observations and their receipt.</p></section>}</>}</main>
}
