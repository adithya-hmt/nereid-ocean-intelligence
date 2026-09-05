import type { QueryPlan } from '../lib/types'

export function QueryPlanPanel({ plan }: { plan: QueryPlan }) {
  const [west, south, east, north] = plan.bbox ?? [0, 0, 0, 0]
  const dates = plan.start_date && plan.end_date ? `${new Date(`${plan.start_date}T00:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} — ${new Date(`${plan.end_date}T00:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}` : 'Date range required'
  return <section className="plan-panel" aria-labelledby="plan-heading"><h2 id="plan-heading">Parsed investigation plan</h2><dl><div><dt>Area</dt><dd>{west}°E to {east}°E · {south}°N to {north}°N</dd></div><div><dt>Window</dt><dd>{dates}</dd></div><div><dt>Policy</dt><dd>{plan.qc_mode === 'research' ? 'Research' : 'Exploratory'}</dd></div><div><dt>Parameters</dt><dd>{plan.parameters.join(', ')}</dd></div></dl></section>
}
