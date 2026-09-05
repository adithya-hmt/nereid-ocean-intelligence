import type { ResultEnvelope } from '../lib/types'

type Cell = { left_profile_index: number; right_profile_index: number; depth_m: number; temperature: number | null; salinity: number | null }
type Coordinate = { wmo: string; cycle: number }
type Section = { observation_coordinates?: Coordinate[]; section_cells?: Cell[]; masked_gaps?: { reason: string }[] }

const left = 30
const top = 20
const plotWidth = 260
const plotHeight = 80

export function CrossSectionPlot({ result }: { result: ResultEnvelope }) {
  const section = result.data[0] as Section | undefined
  if (!section?.section_cells) return null
  const cells = section.section_cells
  const profileCount = Math.max(section.observation_coordinates?.length ?? 0, ...cells.map((cell) => cell.right_profile_index + 1), 2)
  const minDepth = Math.min(...cells.map((cell) => cell.depth_m))
  const maxDepth = Math.max(...cells.map((cell) => cell.depth_m))
  const depthRange = maxDepth - minDepth || 1
  const profileSpacing = plotWidth / (profileCount - 1)
  const depthSpacing = Array.from(new Set(cells.map((cell) => cell.depth_m))).sort((a, b) => a - b).map((depth, index, depths) => index ? depth - depths[index - 1] : depths[1] - depth).find((spacing) => Number.isFinite(spacing) && spacing > 0) ?? depthRange
  const cellHeight = Math.max(6, Math.min(plotHeight / 2, depthSpacing / depthRange * plotHeight))
  const x = (cell: Cell) => left + ((cell.left_profile_index + cell.right_profile_index) / 2) * profileSpacing - profileSpacing / 2
  const y = (depth: number) => top + (depth - minDepth) / depthRange * plotHeight - cellHeight / 2

  return <section className="section-plot" aria-labelledby="section-heading"><h2 id="section-heading">Gap-masked cross-section</h2><p>Cells across unsupported observations remain blank; values are never smoothed across a gap.</p><svg viewBox="0 0 320 120" role="img" aria-label="Gap-masked temperature cross-section">{cells.map((cell) => <rect key={`${cell.left_profile_index}-${cell.right_profile_index}-${cell.depth_m}`} x={x(cell)} y={y(cell.depth_m)} width={profileSpacing} height={cellHeight} className={cell.temperature === null ? 'masked-cell' : 'section-cell'} />)}{section.observation_coordinates?.map((coordinate, index) => <circle key={`${coordinate.wmo}-${coordinate.cycle}`} cx={left + index * profileSpacing} cy="112" r="4" className="observation-marker"><title>{coordinate.wmo} / cycle {coordinate.cycle}</title></circle>)}</svg><table aria-label="Cross-section observations"><caption>Cross-section observations</caption><thead><tr><th>Depth</th><th>Temperature</th><th>Salinity</th><th>Status</th></tr></thead><tbody>{cells.map((cell) => <tr key={`${cell.left_profile_index}-${cell.right_profile_index}-${cell.depth_m}`}><td>{cell.depth_m} m</td><td>{cell.temperature === null ? 'masked' : `${cell.temperature.toFixed(2)} °C`}</td><td>{cell.salinity === null ? 'masked' : `${cell.salinity.toFixed(3)} g kg⁻¹`}</td><td>{cell.temperature === null ? section.masked_gaps?.[0]?.reason?.replace('_', ' ') ?? 'masked' : 'observed'}</td></tr>)}</tbody></table></section>
}
