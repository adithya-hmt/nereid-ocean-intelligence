import { useMemo, useState } from 'react'
import type { ProfileIdentifier, ResultEnvelope } from '../lib/types'

type Observation = { depth: number; temperatureRaw: number | null; temperatureBest: number | null; salinityRaw: number | null; salinityBest: number | null; wmo: string; cycle: number; source_profile_index: number }
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const profileKey = (row: ProfileIdentifier) => `${row.wmo}/${row.cycle}/${row.source_profile_index}`

export function ProfilePlot({ result, selections }: { result: ResultEnvelope; selections: ProfileIdentifier[] }) {
  const [kind, setKind] = useState<'best' | 'raw'>('best')
  const observations = useMemo(() => result.data.flatMap((row): Observation[] => {
    const depth = row.depth_m
    if (!finite(depth) || typeof row.wmo !== 'string' || !finite(row.cycle) || !finite(row.source_profile_index)) return []
    return [{ depth, temperatureRaw: finite(row.temperature_raw) ? row.temperature_raw : null, temperatureBest: finite(row.conservative_temperature) ? row.conservative_temperature : null, salinityRaw: finite(row.salinity_raw) ? row.salinity_raw : null, salinityBest: finite(row.absolute_salinity) ? row.absolute_salinity : null, wmo: row.wmo, cycle: row.cycle, source_profile_index: row.source_profile_index }]
  }), [result])
  const selected = selections.map((selection) => ({ selection, levels: observations.filter((row) => profileKey(row) === profileKey(selection)) })).filter(({ levels }) => levels.length)
  if (!selected.length) return null
  const variables = kind === 'best' ? ['Conservative Temperature (degC)', 'Absolute Salinity (g kg-1)'] : ['in-situ Temperature (degC)', 'Practical Salinity (g kg-1)']
  return <section className="profile-section" aria-labelledby="profile-heading"><div className="section-title"><h2 id="profile-heading">Native profile observations</h2><p>Each source representation remains separate.</p></div><fieldset className="observation-switch"><legend>Displayed values</legend><label><input type="radio" name="observation-kind" checked={kind === 'best'} onChange={() => setKind('best')} /> Best adjusted</label><label><input type="radio" name="observation-kind" checked={kind === 'raw'} onChange={() => setKind('raw')} /> Raw observations</label></fieldset>{selected.map(({ selection, levels }) => <ProfilePanel key={profileKey(selection)} levels={levels} kind={kind} variables={variables} />)}</section>
}

function ProfilePanel({ levels, kind, variables }: { levels: Observation[]; kind: 'best' | 'raw'; variables: string[] }) {
  const usable = levels.filter((row) => finite(kind === 'best' ? row.temperatureBest : row.temperatureRaw) && finite(kind === 'best' ? row.salinityBest : row.salinityRaw))
  const first = levels[0]
  if (!usable.length) return <article className="profile-panel" aria-label={`Profile ${first.wmo} cycle ${first.cycle} representation ${first.source_profile_index}`}><h3>{first.wmo} / cycle {first.cycle} / representation {first.source_profile_index}</h3><p role="status">Insufficient evidence: this representation has no complete {variables[0]} and {variables[1]} observations.</p></article>
  const maxDepth = Math.max(...usable.map((row) => row.depth), 1)
  const temperatures = usable.map((row) => (kind === 'best' ? row.temperatureBest : row.temperatureRaw)!)
  const salinities = usable.map((row) => (kind === 'best' ? row.salinityBest : row.salinityRaw)!)
  const scale = (values: number[], value: number) => { const low = Math.min(...values); const high = Math.max(...values); return 38 + (value - low) / (high - low || 1) * 100 }
  const label = `${first.wmo} cycle ${first.cycle} representation ${first.source_profile_index}: ${variables[0]} and ${variables[1]}, depth increasing downward`
  return <article className="profile-panel" aria-label={`Profile ${first.wmo} cycle ${first.cycle} representation ${first.source_profile_index}`}><h3>{first.wmo} / cycle {first.cycle} / representation {first.source_profile_index}</h3><svg viewBox="0 0 300 240" role="img" aria-label={label} aria-describedby={`profile-description-${profileKey(first)}`} className="profile-plot"><desc id={`profile-description-${profileKey(first)}`}>Separate source representation. {variables[0]} and {variables[1]}; depth axis increases downward.</desc><text x="20" y="18">{variables[0]}</text><text x="165" y="18">{variables[1]}</text><text x="4" y="220">Depth (m) ↓</text><line x1="20" y1="32" x2="20" y2="220" />{usable.map((row, index) => <g key={`${row.depth}-${index}`}><circle cx={scale(temperatures, temperatures[index])} cy={32 + row.depth / maxDepth * 168} r="4" className="temperature-point" /><circle cx={165 + (scale(salinities, salinities[index]) - 38)} cy={32 + row.depth / maxDepth * 168} r="4" className="salinity-point" /></g>)}</svg><table aria-label={`Profile observations for ${first.wmo} cycle ${first.cycle} representation ${first.source_profile_index}`}><caption>{kind === 'best' ? 'Best adjusted TEOS-10 observations' : 'Raw in-situ observations'}</caption><thead><tr><th>Depth (m)</th><th>{variables[0]}</th><th>{variables[1]}</th></tr></thead><tbody>{usable.map((row) => <tr key={row.depth}><td>{row.depth}</td><td>{(kind === 'best' ? row.temperatureBest : row.temperatureRaw)!.toFixed(2)}</td><td>{(kind === 'best' ? row.salinityBest : row.salinityRaw)!.toFixed(3)}</td></tr>)}</tbody></table></article>
}
