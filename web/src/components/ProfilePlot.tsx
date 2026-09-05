import { useMemo, useState } from 'react'
import type { ResultEnvelope } from '../lib/types'

type Observation = { depth: number; temperatureRaw: number; temperatureBest: number; salinityRaw: number; salinityBest: number; wmo: string; cycle: number }
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export function ProfilePlot({ result }: { result: ResultEnvelope }) {
  const [kind, setKind] = useState<'best' | 'raw'>('best')
  const observations = useMemo(() => result.data.flatMap((row): Observation[] => {
    const { depth_m: depth, temperature_raw: temperatureRaw, temperature_best: temperatureBest, salinity_raw: salinityRaw, salinity_best: salinityBest } = row
    if (!finite(depth) || !finite(temperatureRaw) || !finite(temperatureBest) || !finite(salinityRaw) || !finite(salinityBest)) return []
    return [{ depth, temperatureRaw, temperatureBest, salinityRaw, salinityBest, wmo: String(row.wmo), cycle: Number(row.cycle) }]
  }), [result])
  if (!observations.length) return null
  const maxDepth = Math.max(...observations.map((row) => row.depth), 1)
  const temp = observations.map((row) => kind === 'best' ? row.temperatureBest : row.temperatureRaw)
  const salinity = observations.map((row) => kind === 'best' ? row.salinityBest : row.salinityRaw)
  const scale = (values: number[], value: number) => { const low = Math.min(...values); const high = Math.max(...values); return 38 + (value - low) / (high - low || 1) * 224 }
  return <section className="profile-section" aria-labelledby="profile-heading"><div className="section-title"><h2 id="profile-heading">Native profile observations</h2><p>{observations[0].wmo} / cycle {observations[0].cycle}</p></div><fieldset className="observation-switch"><legend>Displayed values</legend><label><input type="radio" name="observation-kind" checked={kind === 'best'} onChange={() => setKind('best')} /> Best adjusted</label><label><input type="radio" name="observation-kind" checked={kind === 'raw'} onChange={() => setKind('raw')} /> Raw observations</label></fieldset><svg viewBox="0 0 300 240" role="img" aria-label="Temperature profile" className="profile-plot"><text x="20" y="18">Temperature (°C)</text><text x="180" y="18">Salinity (g kg⁻¹)</text><line x1="20" y1="32" x2="20" y2="220" /><line x1="170" y1="32" x2="170" y2="220" />{observations.map((row, index) => <g key={`${row.depth}-${index}`}><circle cx={scale(temp, temp[index])} cy={32 + row.depth / maxDepth * 188} r="4" className="temperature-point" /><circle cx={170 + (scale(salinity, salinity[index]) - 38) * 0.55} cy={32 + row.depth / maxDepth * 188} r="4" className="salinity-point" /></g>)}</svg><p className="current-observation">At {observations[0].depth.toFixed(0)} m: {temp[0].toFixed(2)} °C · {salinity[0].toFixed(2)} g kg⁻¹</p></section>
}
