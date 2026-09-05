import { useState } from 'react'

import type { TrajectoryRow } from '../lib/geometry'

type Props = { rows: readonly TrajectoryRow[]; label?: string }

const project = (row: TrajectoryRow) => ({ x: (row.longitude + 180) / 360 * 560 + 20, y: (90 - row.latitude) / 180 * 260 + 20 })

export function TrajectoryFallback({ rows, label = '2D longitude/latitude fallback' }: Props) {
  const [selected, setSelected] = useState(0)
  const current = rows[selected]
  return <div className="trajectory-fallback"><p>{label}</p><svg viewBox="0 0 600 300" role="img" aria-label="Trajectory points projected by longitude and latitude"><rect x="20" y="20" width="560" height="260" fill="none" stroke="currentColor" />{rows.map((row, index) => {
    const point = project(row)
    const choose = () => setSelected(index)
    return <circle key={`${row.wmo}-${row.cycle}-${row.timestamp}-${index}`} cx={point.x} cy={point.y} r={index === selected ? 5 : 3} className="fallback-point" tabIndex={0} role="button" aria-label={`Select ${row.wmo}, cycle ${row.cycle}`} aria-pressed={index === selected} onClick={choose} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose() } }} />
  })}</svg>{current && <p className="trajectory-readout">Selected: {current.longitude.toFixed(3)}° longitude · {current.latitude.toFixed(3)}° latitude · {current.depth_m.toFixed(1)} m depth · {new Date(current.timestamp).toISOString()} · WMO {current.wmo}, cycle {current.cycle}</p>}</div>
}
