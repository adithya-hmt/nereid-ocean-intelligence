'use client'

import { useMemo, useRef, useState } from 'react'
import { ApiError, deriveSection, executeQuery, interpretQuestion } from '../lib/api'
import { createBenchmarkRows } from '../lib/benchmark-data'
import { isTrajectoryRow } from '../lib/geometry'
import type { ProfileIdentifier, QueryPlan, ResultEnvelope, SectionRequest } from '../lib/types'
import { CrossSectionPlot } from './CrossSectionPlot'
import { ProfileMetrics } from './ProfileMetrics'
import { ProfilePlot } from './ProfilePlot'
import { QueryControls } from './QueryControls'
import { QueryPlanPanel } from './QueryPlanPanel'
import { ScientificReceipt } from './ScientificReceipt'
import { TrajectoryGlobe } from './TrajectoryGlobe'

const winningPlan: QueryPlan = { operation: 'find_profiles', bbox: [60, 0, 80, 20], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP', 'PSAL'], qc_mode: 'research', row_limit: 10000 }
type ExactProfileIdentifier = ProfileIdentifier & { source_profile_index: number }
type Props = { initialResult?: ResultEnvelope; benchmark?: boolean; emptyBenchmark?: boolean }
const identity = (item: ProfileIdentifier) => `${item.wmo}/${item.cycle}/${item.direction}/${item.source_profile_index}`

function availableRepresentations(result: ResultEnvelope | undefined): ExactProfileIdentifier[] {
  if (!result) return []
  const representations = new Map<string, ExactProfileIdentifier>()
  for (const row of result.data) {
    const direction = row.direction
    if (typeof row.wmo !== 'string' || typeof row.cycle !== 'number' || typeof row.source_profile_index !== 'number' || (direction !== 'A' && direction !== 'D')) continue
    const representation: ExactProfileIdentifier = { wmo: row.wmo, cycle: row.cycle, direction, source_profile_index: row.source_profile_index }
    representations.set(identity(representation), representation)
  }
  return Array.from(representations.values()).sort((left, right) => identity(left).localeCompare(identity(right)))
}

export function InvestigationWorkspace({ initialResult, benchmark = false, emptyBenchmark = false }: Props) {
  const benchmarkRows = useMemo(() => benchmark && !emptyBenchmark ? createBenchmarkRows(100_000) : [], [benchmark, emptyBenchmark])
  const [plan, setPlan] = useState<QueryPlan>(winningPlan)
  const [question, setQuestion] = useState('')
  const [plannerWarning, setPlannerWarning] = useState<string | undefined>()
  const [result, setResult] = useState<ResultEnvelope | undefined>(initialResult)
  const [selections, setSelections] = useState<ExactProfileIdentifier[]>(() => availableRepresentations(initialResult).slice(0, 2))
  const [section, setSection] = useState<ResultEnvelope | undefined>()
  const [loading, setLoading] = useState(false)
  const [sectionLoading, setSectionLoading] = useState(false)
  const [planning, setPlanning] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const [sectionError, setSectionError] = useState<string | undefined>()
  const request = useRef<AbortController | undefined>(undefined)
  const plannerRequest = useRef<AbortController | undefined>(undefined)
  const executionVersion = useRef(0)
  const plannerVersion = useRef(0)
  const sectionRequest = useRef<AbortController | undefined>(undefined)

  const invalidateSection = () => {
    sectionRequest.current?.abort()
    sectionRequest.current = undefined
    setSection(undefined)
    setSectionError(undefined)
    setSectionLoading(false)
  }

  const invalidateExecution = () => {
    executionVersion.current += 1
    request.current?.abort()
    request.current = undefined
    setResult(undefined)
    setSelections([])
    invalidateSection()
  }

  const updatePlan = (nextPlan: QueryPlan) => {
    invalidateExecution()
    plannerVersion.current += 1
    plannerRequest.current?.abort()
    setPlan(nextPlan)
  }

  const updateQuestion = (nextQuestion: string) => {
    plannerVersion.current += 1
    plannerRequest.current?.abort()
    setQuestion(nextQuestion)
  }

  const updateSelections = (nextSelections: ExactProfileIdentifier[]) => {
    invalidateSection()
    setSelections(nextSelections)
  }

  const submit = async () => {
    request.current?.abort()
    invalidateSection()
    const controller = new AbortController()
    const version = ++executionVersion.current
    request.current = controller
    setLoading(true); setError(undefined)
    try {
      const nextResult = await executeQuery(plan, controller.signal)
      if (request.current === controller && executionVersion.current === version) {
        setResult(nextResult)
        setSelections(availableRepresentations(nextResult).slice(0, 2))
      }
    } catch (caught) {
      if (request.current === controller && executionVersion.current === version && !(caught instanceof DOMException && caught.name === 'AbortError')) setError(caught instanceof ApiError ? `${caught.status}: ${caught.message}` : 'The investigation could not be updated. Check the snapshot and try again.')
    } finally { if (request.current === controller && executionVersion.current === version) setLoading(false) }
  }

  const requestSection = async () => {
    if (!result || selections.length < 2) return
    sectionRequest.current?.abort()
    const controller = new AbortController(); sectionRequest.current = controller
    setSectionLoading(true); setSectionError(undefined)
    const request: SectionRequest = { profile_ids: selections, qc_mode: result.query_plan.qc_mode, depth_step_m: 10, max_time_gap_hours: 168, max_distance_km: 500, max_vertical_gap_m: 100 }
    try {
      const nextSection = await deriveSection(request, controller.signal)
      if (sectionRequest.current === controller) setSection(nextSection)
    } catch (caught) {
      if (sectionRequest.current === controller && !(caught instanceof DOMException && caught.name === 'AbortError')) setSectionError(caught instanceof ApiError ? `${caught.status}: ${caught.message}` : 'The server refused this section because the exact selected representations have insufficient evidence.')
    } finally { if (sectionRequest.current === controller) setSectionLoading(false) }
  }

  const interpret = async () => {
    plannerRequest.current?.abort()
    const controller = new AbortController()
    const version = ++plannerVersion.current
    plannerRequest.current = controller
    setPlanning(true); setPlannerWarning(undefined)
    try {
      const response = await interpretQuestion(question, controller.signal)
      if (plannerRequest.current === controller && plannerVersion.current === version) {
        if (response.plan) updatePlan(response.plan)
        setPlannerWarning(response.warnings[0])
      }
    } catch (caught) {
      if (plannerRequest.current === controller && plannerVersion.current === version && !(caught instanceof DOMException && caught.name === 'AbortError')) setPlannerWarning(caught instanceof ApiError ? `AI interpretation unavailable—filters still work. ${caught.message}` : 'AI interpretation unavailable—filters still work. Use explicit filters.')
    } finally { if (plannerRequest.current === controller && plannerVersion.current === version) setPlanning(false) }
  }

  const trajectoryRows = result?.data.filter(isTrajectoryRow) ?? []
  return <main className="workspace"><header className="workspace-header"><h1>Nereid Ocean Investigation</h1><p>Traceable ARGO evidence for a bounded question near 10°N, 70°E.</p></header>{benchmark ? <><TrajectoryGlobe rows={benchmarkRows} benchmark drawPoints={!emptyBenchmark} /><p className="benchmark-label">Declared browser and hardware are recorded separately from measured values in the rendering benchmark evidence.</p></> : <><QueryControls plan={plan} question={question} loading={loading} planning={planning} plannerWarning={plannerWarning} onChange={updatePlan} onQuestionChange={updateQuestion} onInterpret={interpret} onSubmit={submit} onExample={() => updatePlan(winningPlan)} /><QueryPlanPanel plan={plan} />{error && <p className="status error" role="alert">{error}</p>}{result ? <><section className="visualization" aria-labelledby="visualization-heading"><h2 id="visualization-heading">Investigation view</h2>{trajectoryRows.length ? <TrajectoryGlobe key={`${trajectoryRows.length}-${trajectoryRows[0].timestamp}`} rows={trajectoryRows} /> : result.data.length ? <p className="status empty">The returned observations have no complete longitude, latitude, depth, and time coordinates for a truthful trajectory.</p> : <p className="status empty">{result.warnings[0] ?? 'No observations are available for this bounded request.'}</p>}</section><ProfilePlot result={result} selections={selections} /><ProfileMetrics result={result} selections={selections} /><section className="section-request" aria-labelledby="section-request-heading"><h2 id="section-request-heading">Derived cross-section</h2><p>Uses exactly the selected representations; unsupported gaps remain masked.</p><button className="primary-button" type="button" disabled={selections.length < 2 || sectionLoading} onClick={() => void requestSection()}>{sectionLoading ? 'Deriving section…' : 'Derive section from selected representations'}</button>{selections.length < 2 && <p role="status">Select at least two exact representations before requesting a section.</p>}{sectionError && <p className="status error" role="alert">{sectionError}</p>}</section>{section && <CrossSectionPlot result={section} />}<ScientificReceipt result={result} selections={selections} onSelectionChange={updateSelections} /></> : <section className="visualization empty" aria-live="polite"><h2>Investigation view</h2><p>Run the bounded query to inspect source-faithful observations and their receipt.</p></section>}</>}</main>
}
