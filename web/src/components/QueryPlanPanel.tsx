import type { QueryPlan } from '../lib/types'

const allParameters = ['TEMP', 'PSAL', 'PRES']

export function QueryPlanPanel({ plan }: { plan: QueryPlan }) {
  const identities = plan.profile_ids?.map((item) => `${item.wmo}/${item.cycle}/${item.direction}/${item.source_profile_index}`).join(', ') || 'None'
  const geographic = plan.bbox ? `${plan.bbox[0]}°E to ${plan.bbox[2]}°E · ${plan.bbox[1]}°N to ${plan.bbox[3]}°N` : 'None'
  const dates = plan.start_date && plan.end_date ? `${plan.start_date} — ${plan.end_date}` : 'None'
  return <section className="plan-panel" aria-labelledby="plan-heading"><h2 id="plan-heading">Parsed investigation plan</h2><dl>
    <div><dt>Operation</dt><dd>{plan.operation}</dd></div>
    <div><dt>Area</dt><dd>{geographic}</dd></div><div><dt>Window</dt><dd>{dates}</dd></div>
    <div><dt>WMO / cycle / direction</dt><dd>{plan.wmo ? `${plan.wmo}/${plan.cycle}/${plan.direction}` : 'None'}</dd></div>
    <div><dt>Exact profile IDs</dt><dd>{identities}</dd></div>
    <div><dt>Nearest float count</dt><dd>{plan.float_count ?? 'None'}</dd></div>
    <div><dt>Row limit</dt><dd>{plan.row_limit}</dd></div><div><dt>Policy</dt><dd>{plan.qc_mode === 'research' ? 'Research' : 'Exploratory'}</dd></div>
    <div><dt>Parameters</dt><dd>{(plan.parameters.length ? plan.parameters : allParameters).join(', ')}</dd></div>
  </dl></section>
}
