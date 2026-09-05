import type { Operation, ProfileIdentifier, QueryPlan } from '../lib/types'

type Props = { plan: QueryPlan; question: string; loading: boolean; planning: boolean; plannerWarning?: string; onChange: (plan: QueryPlan) => void; onQuestionChange: (question: string) => void; onInterpret: () => void; onSubmit: () => void; onExample: () => void }
const operations: Operation[] = ['find_profiles', 'nearest_floats', 'get_profile', 'compare_profiles', 'derive_section']
const geographic = (operation: Operation) => operation === 'find_profiles' || operation === 'nearest_floats'
const exact = (operation: Operation) => operation === 'compare_profiles' || operation === 'derive_section'
const defaults = (operation: Operation, plan: QueryPlan): QueryPlan => geographic(operation) ? { operation, bbox: [60, 0, 80, 20], start_date: '2023-03-01', end_date: '2023-03-31', parameters: plan.parameters, qc_mode: plan.qc_mode, row_limit: plan.row_limit, ...(operation === 'nearest_floats' ? { float_count: 2 } : {}) } : operation === 'get_profile' ? { operation, wmo: '', cycle: 0, direction: 'A', parameters: plan.parameters, qc_mode: plan.qc_mode, row_limit: plan.row_limit } : { operation, profile_ids: [{ wmo: '', cycle: 0, direction: 'A', source_profile_index: 0 }, { wmo: '', cycle: 1, direction: 'A', source_profile_index: 0 }], parameters: plan.parameters, qc_mode: plan.qc_mode, row_limit: plan.row_limit }

export function QueryControls({ plan, question, loading, planning, plannerWarning, onChange, onQuestionChange, onInterpret, onSubmit, onExample }: Props) {
  const bbox = plan.bbox ?? [60, 0, 80, 20]
  const updateBbox = (index: number, value: string) => { const next = [...bbox] as [number, number, number, number]; next[index] = Number(value); onChange({ ...plan, bbox: next }) }
  const updateParameters = (parameter: QueryPlan['parameters'][number]) => onChange({ ...plan, parameters: plan.parameters.length === 0 ? (['TEMP', 'PSAL', 'PRES'] as const).filter((item) => item !== parameter) : plan.parameters.includes(parameter) ? plan.parameters.filter((item) => item !== parameter) : [...plan.parameters, parameter] })
  const idsText = (plan.profile_ids ?? []).map((item) => `${item.wmo}/${item.cycle}/${item.direction}/${item.source_profile_index ?? ''}`).join('\n')
  const updateIds = (text: string) => {
    const profile_ids: ProfileIdentifier[] = text.split('\n').filter(Boolean).map((line) => {
      const [wmo, cycle, direction, source_profile_index] = line.trim().split('/')
      return { wmo, cycle: Number(cycle), direction: direction as 'A' | 'D', source_profile_index: Number(source_profile_index) }
    })
    onChange({ ...plan, profile_ids })
  }
  return <form className="query-controls" onSubmit={(event) => { event.preventDefault(); onSubmit() }}>
    <div className="query-heading"><h2>Set the evidence boundary</h2><button type="button" className="text-button" onClick={onExample}>Use March 2023 example</button></div>
    <label>Question (optional)<input type="text" value={question} onChange={(event) => onQuestionChange(event.target.value)} placeholder="Describe a bounded ARGO question" /></label>
    <button type="button" className="text-button" onClick={onInterpret} disabled={!question.trim() || planning}>{planning ? 'Interpreting question…' : 'Interpret question'}</button>
    {plannerWarning && <p className="status planner-warning" role="status">{plannerWarning}</p>}
    <div className="control-grid">
      <label>Operation<select aria-label="Operation" value={plan.operation} onChange={(event) => onChange(defaults(event.target.value as Operation, plan))}>{operations.map((operation) => <option key={operation} value={operation}>{operation}</option>)}</select></label>
      <label>Row limit<input aria-label="Row limit" type="number" min="1" max="100000" value={plan.row_limit} onChange={(event) => onChange({ ...plan, row_limit: Number(event.target.value) })} /></label>
      <label>Quality policy<select value={plan.qc_mode} onChange={(event) => onChange({ ...plan, qc_mode: event.target.value as QueryPlan['qc_mode'] })}><option value="research">Research — QC 1</option><option value="exploratory">Exploratory — QC 1–2</option></select></label>
      {(['TEMP', 'PSAL', 'PRES'] as const).map((parameter) => <label key={parameter}><input type="checkbox" checked={plan.parameters.length === 0 || plan.parameters.includes(parameter)} onChange={() => updateParameters(parameter)} />{parameter}</label>)}
      {geographic(plan.operation) && <>{(['West longitude', 'South latitude', 'East longitude', 'North latitude'] as const).map((label, index) => <label key={label}>{label}<input type="number" value={bbox[index]} onChange={(event) => updateBbox(index, event.target.value)} /></label>)}<label>Start date<input type="date" value={plan.start_date ?? ''} onChange={(event) => onChange({ ...plan, start_date: event.target.value })} /></label><label>End date<input type="date" value={plan.end_date ?? ''} onChange={(event) => onChange({ ...plan, end_date: event.target.value })} /></label></>}
      {plan.operation === 'nearest_floats' && <label>Nearest float count<input type="number" min="1" max="100" value={plan.float_count ?? 1} onChange={(event) => onChange({ ...plan, float_count: Number(event.target.value) })} /></label>}
      {plan.operation === 'get_profile' && <><label>WMO<input value={plan.wmo ?? ''} onChange={(event) => onChange({ ...plan, wmo: event.target.value })} /></label><label>Cycle<input type="number" value={plan.cycle ?? 0} onChange={(event) => onChange({ ...plan, cycle: Number(event.target.value) })} /></label><label>Direction<select value={plan.direction ?? 'A'} onChange={(event) => onChange({ ...plan, direction: event.target.value as 'A' | 'D' })}><option>A</option><option>D</option></select></label></>}
      {exact(plan.operation) && <label>Exact profile IDs (wmo/cycle/direction/source_profile_index, one per line)<textarea aria-label="Exact profile IDs" value={idsText} onChange={(event) => updateIds(event.target.value)} /></label>}
    </div>
    <button className="primary-button" disabled={loading}>{loading ? 'Updating investigation…' : 'Run investigation'}</button>
  </form>
}
