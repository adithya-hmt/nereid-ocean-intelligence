import type { MaskedGap, ResultEnvelope, SectionCell, SectionData, SectionObservationCoordinate } from '../lib/types'

const left = 30
const top = 20
const plotWidth = 260
const plotHeight = 80

const coordinateIdentity = (coordinate: SectionObservationCoordinate) => `${coordinate.wmo} / cycle ${coordinate.cycle} / representation ${coordinate.source_profile_index} / ${coordinate.vertical_sampling_scheme}`
const coordinateTitle = (coordinate: SectionObservationCoordinate) => `Observed coordinate: ${coordinateIdentity(coordinate)}; latitude ${coordinate.latitude}; longitude ${coordinate.longitude}; timestamp ${coordinate.timestamp}`
const cellKey = (cell: SectionCell) => `${cell.left_profile_index}-${cell.right_profile_index}-${cell.depth_m}`
const gapKey = (gap: Pick<MaskedGap, 'left_profile_index' | 'right_profile_index'>) => `${gap.left_profile_index}-${gap.right_profile_index}`

export function CrossSectionPlot({ result }: { result: ResultEnvelope }) {
  const section = result.data[0] as SectionData | undefined
  if (!section?.section_cells?.length) return null
  const cells = section.section_cells
  const coordinates = section.observation_coordinates ?? []
  const gaps = new Map((section.masked_gaps ?? []).map((gap) => [gapKey(gap), gap.reason]))
  const profileCount = Math.max(coordinates.length, ...cells.map((cell) => cell.right_profile_index + 1), 2)
  const minDepth = Math.min(...cells.map((cell) => cell.depth_m))
  const maxDepth = Math.max(...cells.map((cell) => cell.depth_m))
  const depthRange = maxDepth - minDepth || 1
  const profileSpacing = plotWidth / (profileCount - 1)
  const depthSpacing = Array.from(new Set(cells.map((cell) => cell.depth_m))).sort((a, b) => a - b).map((depth, index, depths) => index ? depth - depths[index - 1] : depths[1] - depth).find((spacing) => Number.isFinite(spacing) && spacing > 0) ?? depthRange
  const cellHeight = Math.max(6, Math.min(plotHeight / 2, depthSpacing / depthRange * plotHeight))
  const x = (cell: SectionCell) => left + ((cell.left_profile_index + cell.right_profile_index) / 2) * profileSpacing - profileSpacing / 2
  const y = (depth: number) => top + (depth - minDepth) / depthRange * plotHeight - cellHeight / 2
  const representations = (cell: SectionCell) => [coordinates[cell.left_profile_index], coordinates[cell.right_profile_index]].filter((coordinate): coordinate is SectionObservationCoordinate => coordinate !== undefined).map(coordinateIdentity).join(' to ')
  const status = (cell: SectionCell) => {
    if (cell.temperature !== null || cell.salinity !== null) return 'interpolated derived'
    const reason = gaps.get(gapKey(cell))
    return reason ? reason.replaceAll('_', ' ') : 'masked'
  }

  return <section className="section-plot" aria-labelledby="section-heading"><h2 id="section-heading">Gap-masked cross-section</h2><p>Cells across unsupported observations remain blank; values are never smoothed across a gap.</p><svg viewBox="0 0 320 120" role="img" aria-label="Gap-masked temperature cross-section">{cells.map((cell) => <rect key={cellKey(cell)} x={x(cell)} y={y(cell.depth_m)} width={profileSpacing} height={cellHeight} className={cell.temperature === null ? 'masked-cell' : 'section-cell'} />)}{coordinates.map((coordinate, index) => <circle key={`${coordinate.wmo}-${coordinate.cycle}-${coordinate.source_profile_index}-${coordinate.vertical_sampling_scheme}-${coordinate.latitude}-${coordinate.longitude}-${coordinate.timestamp}`} cx={left + index * profileSpacing} cy="112" r="4" className="observation-marker"><title>{coordinateTitle(coordinate)}</title></circle>)}</svg><table aria-label="Cross-section observations"><caption>Cross-section observations</caption><thead><tr><th>Depth</th><th>Between representations</th><th>Temperature</th><th>Salinity</th><th>Status</th></tr></thead><tbody>{cells.map((cell) => <tr key={cellKey(cell)}><td>{cell.depth_m} m</td><td>{representations(cell)}</td><td>{cell.temperature === null ? 'masked' : `${cell.temperature.toFixed(2)} °C`}</td><td>{cell.salinity === null ? 'masked' : `${cell.salinity.toFixed(3)} g kg⁻¹`}</td><td>{status(cell)}</td></tr>)}</tbody></table></section>
}
