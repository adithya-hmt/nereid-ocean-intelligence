'use client'

import { useRef, useState } from 'react'

import { ApiError, executeQuery } from '../lib/api'
import type { QueryPlan, ResultEnvelope } from '../lib/types'
import { CrossSectionPlot } from './CrossSectionPlot'
import { ProfilePlot } from './ProfilePlot'
import { QueryControls } from './QueryControls'
import { QueryPlanPanel } from './QueryPlanPanel'
import { ScientificReceipt } from './ScientificReceipt'

const winningPlan: QueryPlan = { operation: 'find_profiles', bbox: [60, 0, 80, 20], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP', 'PSAL'], qc_mode: 'research', row_limit: 10000 }

type Props = { initialResult?: ResultEnvelope }

export function InvestigationWorkspace({ initialResult }: Props) {
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

  return <main className="workspace"><header className="workspace-header"><h1>Nereid Ocean Investigation</h1><p>Traceable ARGO evidence for a bounded question near 10°N, 70°E.</p></header><QueryControls plan={plan} loading={loading} onChange={setPlan} onSubmit={submit} onExample={() => setPlan(winningPlan)} /><QueryPlanPanel plan={plan} />{error && <p className="status error" role="alert">{error}</p>}{result ? <><section className="visualization" aria-labelledby="visualization-heading"><h2 id="visualization-heading">Investigation view</h2>{result.data.length ? <p>Native observations are shown below. A trajectory view is not part of this release.</p> : <p className="status empty">{result.warnings[0] ?? 'No observations are available for this bounded request.'}</p>}</section><ProfilePlot result={result} /><CrossSectionPlot result={result} /><ScientificReceipt result={result} /></> : <section className="visualization empty" aria-live="polite"><h2>Investigation view</h2><p>Run the bounded query to inspect source-faithful observations and their receipt.</p></section>}</main>
}
