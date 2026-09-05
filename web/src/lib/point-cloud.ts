import { BufferAttribute, BufferGeometry, DynamicDrawUsage } from 'three'

import { buildTrajectoryBuffers, type TrajectoryRow } from './geometry'

export function createTrajectoryGeometry(capacity: number): BufferGeometry {
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(new Float32Array(capacity * 3), 3).setUsage(DynamicDrawUsage))
  geometry.setAttribute('color', new BufferAttribute(new Float32Array(capacity * 3), 3).setUsage(DynamicDrawUsage))
  geometry.setDrawRange(0, 0)
  return geometry
}

export function updateTrajectoryGeometry(geometry: BufferGeometry, rows: readonly TrajectoryRow[], exaggeration: number) {
  const buffers = buildTrajectoryBuffers(rows, exaggeration)
  const positions = geometry.getAttribute('position') as BufferAttribute
  const colors = geometry.getAttribute('color') as BufferAttribute
  ;(positions.array as Float32Array).set(buffers.positions)
  ;(colors.array as Float32Array).set(buffers.colors)
  positions.needsUpdate = true
  colors.needsUpdate = true
  geometry.setDrawRange(0, rows.length)
}
