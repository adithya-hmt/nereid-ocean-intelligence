import { describe, expect, it } from 'vitest'

import { createTrajectoryGeometry, updateTrajectoryGeometry } from './point-cloud'

const rows = [
  { longitude: 70, latitude: 10, depth_m: 10, timestamp: '2023-03-01T00:00:00Z', wmo: '1', cycle: 1 },
  { longitude: 71, latitude: 11, depth_m: 20, timestamp: '2023-03-02T00:00:00Z', wmo: '1', cycle: 2 },
]

describe('trajectory point cloud resources', () => {
  it('updates typed attributes and draw range in place for a cutoff change', () => {
    const geometry = createTrajectoryGeometry(rows.length)
    const position = geometry.getAttribute('position')
    const color = geometry.getAttribute('color')
    updateTrajectoryGeometry(geometry, rows, 20)
    updateTrajectoryGeometry(geometry, rows.slice(0, 1), 20)
    expect(geometry.getAttribute('position')).toBe(position)
    expect(geometry.getAttribute('color')).toBe(color)
    expect(geometry.drawRange.count).toBe(1)
    geometry.dispose()
  })
})
