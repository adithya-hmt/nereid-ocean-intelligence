import { useMemo, useState } from 'react'
import type { ProfileIdentifier, ResultEnvelope } from '../lib/types'

type Observation = { depth: number; temperatureRaw: number | null; temperatureBest: number | null; salinityRaw: number | null; salinityBest: number | null; wmo: string; cycle: number; direction: 'A' | 'D'; source_profile_index: number }
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const profileKey = (row: ProfileIdentifier) => `${row.wmo}/${row.cycle}/${row.direction}/${row.source_profile_index}`

export function ProfilePlot({ result, selections }: { result: ResultEnvelope; selections: ProfileIdentifier[] }) {
  const [kind, setKind] = useState<'best' | 'raw'>('best')
  const observations = useMemo(() => result.data.flatMap((row): Observation[] => {
    const depth = row.depth_m
    if (!finite(depth) || typeof row.wmo !== 'string' || !finite(row.cycle) || (row.direction !== 'A' && row.direction !== 'D') || !finite(row.source_profile_index)) return []
    return [{ depth, temperatureRaw: finite(row.temperature_raw) ? row.temperature_raw : null, temperatureBest: finite(row.conservative_temperature) ? row.conservative_temperature : null, salinityRaw: finite(row.salinity_raw) ? row.salinity_raw : null, salinityBest: finite(row.absolute_salinity) ? row.absolute_salinity : null, wmo: row.wmo, cycle: row.cycle, direction: row.direction, source_profile_index: row.source_profile_index }]
  }), [result])
  const selected = selections.map((selection) => ({ selection, levels: observations.filter((row) => profileKey(row) === profileKey(selection)) })).filter(({ levels }) => levels.length)
  if (!selected.length) return null
  const requested = new Set(result.query_plan.parameters.length ? result.query_plan.parameters : ['TEMP', 'PSAL', 'PRES'])
  const variables = kind === 'best' ? ['Conservative Temperature (degC)', 'Absolute Salinity (g kg-1)'] : ['in-situ Temperature (degC)', 'Practical Salinity (PSS-78, unitless)']
  return <section className="profile-section" aria-labelledby="profile-heading"><div className="section-title"><h2 id="profile-heading">Native profile observations</h2><p>Each source representation remains separate.</p></div><fieldset className="observation-switch"><legend>Displayed values</legend><label><input type="radio" name="observation-kind" checked={kind === 'best'} onChange={() => setKind('best')} /> Best adjusted</label><label><input type="radio" name="observation-kind" checked={kind === 'raw'} onChange={() => setKind('raw')} /> Raw observations</label></fieldset>{selected.map(({ selection, levels }) => <ProfilePanel key={profileKey(selection)} levels={levels} kind={kind} variables={variables} showTemperature={requested.has('TEMP')} showSalinity={requested.has('PSAL')} />)}</section>
}

function ProfilePanel({ levels, kind, variables, showTemperature, showSalinity }: { levels: Observation[]; kind: 'best' | 'raw'; variables: string[]; showTemperature: boolean; showSalinity: boolean }) {
  const first = levels[0]
  const temperature = showTemperature ? levels.filter((row) => finite(kind === 'best' ? row.temperatureBest : row.temperatureRaw)) : []
  const salinity = showSalinity ? levels.filter((row) => finite(kind === 'best' ? row.salinityBest : row.salinityRaw)) : []
  if (!temperature.length && !salinity.length) return <article className="profile-panel" aria-label={`Profile ${first.wmo} cycle ${first.cycle} direction ${first.direction} representation ${first.source_profile_index}`}><h3>{first.wmo} / cycle {first.cycle} / {first.direction} / representation {first.source_profile_index}</h3><p role="status">Insufficient evidence: this representation has no requested observations.</p></article>
  const maxDepth = Math.max(...levels.map((row) => row.depth), 1)
  const scale = (values: Observation[], value: number, field: 'temperatureBest' | 'temperatureRaw' | 'salinityBest' | 'salinityRaw') => { const numbers = values.map((row) => row[field]!).filter(finite); const low = Math.min(...numbers); const high = Math.max(...numbers); return 38 + (value - low) / (high - low || 1) * 100 }
  const label = `${first.wmo} cycle ${first.cycle} direction ${first.direction} representation ${first.source_profile_index}: ${temperature.length ? variables[0] : ''}${temperature.length && salinity.length ? ' and ' : ''}${salinity.length ? variables[1] : ''}, depth increasing downward`
  const tempField = kind === 'best' ? 'temperatureBest' : 'temperatureRaw'
  const salinityField = kind === 'best' ? 'salinityBest' : 'salinityRaw'
  return <article className="profile-panel" aria-label={`Profile ${first.wmo} cycle ${first.cycle} direction ${first.direction} representation ${first.source_profile_index}`}><h3>{first.wmo} / cycle {first.cycle} / {first.direction} / representation {first.source_profile_index}</h3><svg viewBox="0 0 300 240" role="img" aria-label={label} aria-describedby={`profile-description-${profileKey(first)}`} className="profile-plot"><desc id={`profile-description-${profileKey(first)}`}>Separate source representation; depth axis increases downward.</desc>{temperature.length > 0 && <text x="20" y="18">{variables[0]}</text>}{salinity.length > 0 && <text x="165" y="18">{variables[1]}</text>}<text x="4" y="220">Depth (m) ↓</text><line x1="20" y1="32" x2="20" y2="220" />{temperature.map((row, index) => <circle key={`t-${row.depth}-${index}`} cx={scale(temperature, row[tempField]!, tempField)} cy={32 + row.depth / maxDepth * 168} r="4" className="temperature-point" />)}{salinity.map((row, index) => <circle key={`s-${row.depth}-${index}`} cx={165 + (scale(salinity, row[salinityField]!, salinityField) - 38)} cy={32 + row.depth / maxDepth * 168} r="4" className="salinity-point" />)}</svg><table aria-label={`Profile observations for ${first.wmo} cycle ${first.cycle} direction ${first.direction} representation ${first.source_profile_index}`}><caption>{kind === 'best' ? 'Best adjusted TEOS-10 observations' : 'Raw in-situ observations'}</caption><thead><tr><th>Depth (m)</th>{showTemperature && <th>{variables[0]}</th>}{showSalinity && <th>{variables[1]}</th>}</tr></thead><tbody>{levels.map((row) => <tr key={row.depth}><td>{row.depth}</td>{showTemperature && <td>{finite(row[tempField]) ? row[tempField]!.toFixed(2) : '—'}</td>}{showSalinity && <td>{finite(row[salinityField]) ? row[salinityField]!.toFixed(3) : '—'}</td>}</tr>)}</tbody></table></article>
}
