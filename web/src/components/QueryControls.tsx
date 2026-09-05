import type { QueryPlan } from '../lib/types'

type Props = { plan: QueryPlan; question: string; loading: boolean; planning: boolean; plannerWarning?: string; onChange: (plan: QueryPlan) => void; onQuestionChange: (question: string) => void; onInterpret: () => void; onSubmit: () => void; onExample: () => void }

export function QueryControls({ plan, question, loading, planning, plannerWarning, onChange, onQuestionChange, onInterpret, onSubmit, onExample }: Props) {
  const bbox = plan.bbox ?? [60, 0, 80, 20]
  const updateBbox = (index: number, value: string) => {
    const next = [...bbox] as [number, number, number, number]
    next[index] = Number(value)
    onChange({ ...plan, bbox: next })
  }
  return <form className="query-controls" onSubmit={(event) => { event.preventDefault(); onSubmit() }}>
    <div className="query-heading"><h2>Set the evidence boundary</h2><button type="button" className="text-button" onClick={onExample}>Use March 2023 example</button></div>
    <label>Question (optional)<input type="text" value={question} onChange={(event) => onQuestionChange(event.target.value)} placeholder="Describe a bounded ARGO question" /></label>
    <button type="button" className="text-button" onClick={onInterpret} disabled={!question.trim() || planning}> {planning ? 'Interpreting question…' : 'Interpret question'}</button>
    {plannerWarning && <p className="status planner-warning" role="status">{plannerWarning}</p>}
    <div className="control-grid">
      {(['West longitude', 'South latitude', 'East longitude', 'North latitude'] as const).map((label, index) => <label key={label}>{label}<input type="number" value={bbox[index]} onChange={(event) => updateBbox(index, event.target.value)} /></label>)}
      <label>Start date<input type="date" value={plan.start_date ?? ''} onChange={(event) => onChange({ ...plan, start_date: event.target.value })} /></label>
      <label>End date<input type="date" value={plan.end_date ?? ''} onChange={(event) => onChange({ ...plan, end_date: event.target.value })} /></label>
      <label>Quality policy<select value={plan.qc_mode} onChange={(event) => onChange({ ...plan, qc_mode: event.target.value as QueryPlan['qc_mode'] })}><option value="research">Research — QC 1</option><option value="exploratory">Exploratory — QC 1–2</option></select></label>
    </div>
    <button className="primary-button" disabled={loading}>{loading ? 'Updating investigation…' : 'Run investigation'}</button>
  </form>
}
