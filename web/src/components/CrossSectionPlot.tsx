import type { ResultEnvelope } from '../lib/types'

type Cell = { left_profile_index: number; right_profile_index: number; depth_m: number; temperature: number | null; salinity: number | null }
type Coordinate = { wmo: string; cycle: number }
type Section = { observation_coordinates?: Coordinate[]; section_cells?: Cell[]; masked_gaps?: { reason: string }[] }

export function CrossSectionPlot({ result }: { result: ResultEnvelope }) {
  const section = result.data[0] as Section | undefined
  if (!section?.section_cells) return null
  return <section className="section-plot" aria-labelledby="section-heading"><h2 id="section-heading">Gap-masked cross-section</h2><p>Cells across unsupported observations remain blank; values are never smoothed across a gap.</p><svg viewBox="0 0 320 120" role="img" aria-label="Gap-masked temperature cross-section">{section.section_cells.map((cell, index) => cell.temperature === null ? <rect key={index} x={30 + index * 28} y={30} width="24" height="65" className="masked-cell" /> : <rect key={index} x={30 + index * 28} y={30} width="24" height="65" className="section-cell" />)}{section.observation_coordinates?.map((coordinate, index) => <circle key={`${coordinate.wmo}-${coordinate.cycle}`} cx={42 + index * 220} cy="103" r="4" className="observation-marker"><title>{coordinate.wmo} / cycle {coordinate.cycle}</title></circle>)}</svg><table aria-label="Cross-section observations"><caption>Cross-section observations</caption><thead><tr><th>Depth</th><th>Temperature</th><th>Salinity</th><th>Status</th></tr></thead><tbody>{section.section_cells.map((cell, index) => <tr key={index}><td>{cell.depth_m} m</td><td>{cell.temperature === null ? 'masked' : `${cell.temperature.toFixed(2)} °C`}</td><td>{cell.salinity === null ? 'masked' : `${cell.salinity.toFixed(3)} g kg⁻¹`}</td><td>{cell.temperature === null ? section.masked_gaps?.[0]?.reason?.replace('_', ' ') ?? 'masked' : 'observed'}</td></tr>)}</tbody></table></section>
}
