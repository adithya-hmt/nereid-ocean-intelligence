import { Fragment } from 'react'
import type { ProfileIdentifier, ProfileMetric, ProfileMetricId, ResultEnvelope } from '../lib/types'

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const identity = (item: ProfileIdentifier) => `${item.wmo}/${item.cycle}/${item.direction}/${item.source_profile_index}`
const metricLabels: Record<ProfileMetricId, string> = {
  principal_thermocline: 'Principal thermocline',
  strongest_salinity_gradient: 'Strongest salinity gradient',
}
const metricIds = Object.keys(metricLabels) as ProfileMetricId[]

function metricsFrom(result: ResultEnvelope): ProfileMetric[] {
  return result.chart_spec.flatMap((spec) => {
    const metrics = spec.profile_metrics
    if (!Array.isArray(metrics)) return []
    return metrics.flatMap((item) => {
      if (typeof item.wmo !== 'string' || !finite(item.cycle) || !finite(item.source_profile_index) || (item.direction !== 'A' && item.direction !== 'D') || !(item.name in metricLabels) || !finite(item.value) || !finite(item.depth_m) || typeof item.units !== 'string' || !finite(item.uncertainty_m) || typeof item.algorithm !== 'string' || typeof item.quality_label !== 'string') return []
      return [{ wmo: item.wmo, cycle: item.cycle, direction: item.direction, source_profile_index: item.source_profile_index, name: item.name, value: item.value, depth_m: item.depth_m, units: item.units, uncertainty_m: item.uncertainty_m, algorithm: item.algorithm, parameters: typeof item.parameters === 'object' && item.parameters !== null ? item.parameters as Record<string, unknown> : {}, quality_label: item.quality_label }]
    })
  })
}

export function ProfileMetrics({ result, selections }: { result: ResultEnvelope; selections: ProfileIdentifier[] }) {
  const metrics = metricsFrom(result)
  const requested = result.query_plan.parameters.length ? result.query_plan.parameters : ['TEMP', 'PSAL', 'PRES']
  if (!selections.length) return null
  return <section className="profile-metrics" aria-labelledby="metrics-heading"><h2 id="metrics-heading">Profile metrics</h2>{selections.map((selection) => {
    const selectedMetrics = metrics.filter((metric) => identity(metric) === identity(selection))
    return <article key={identity(selection)} aria-label={`Metrics for ${identity(selection)}`}><h3>{selection.wmo} / cycle {selection.cycle} / {selection.direction} / representation {selection.source_profile_index}</h3>{metricIds.filter((metricId) => metricId === 'principal_thermocline' ? requested.includes('TEMP') : requested.includes('PSAL')).map((metricId) => {
      const metric = selectedMetrics.find((item) => item.name === metricId)
      const label = metricLabels[metricId]
      return metric ? <dl key={metricId}><dt>{label}</dt><dd>{metric.value} {metric.units} at {metric.depth_m} m</dd><dt>Vertical uncertainty</dt><dd>±{metric.uncertainty_m} m</dd><dt>Method</dt><dd>{metric.algorithm}</dd><dt>QC</dt><dd>{metric.quality_label}</dd>{Object.entries(metric.parameters).filter(([parameter]) => parameter.includes('error')).map(([parameter, value]) => <Fragment key={parameter}><dt>{parameter}</dt><dd>{String(value)}</dd></Fragment>)}</dl> : <p key={metricId} role="status">Insufficient evidence for {label} for {selection.wmo} / cycle {selection.cycle} / {selection.direction} / representation {selection.source_profile_index}.</p>
    })}</article>
  })}</section>
}
