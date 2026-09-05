export interface TrajectoryRow {
  longitude: number
  latitude: number
  depth_m: number
  timestamp: string
  wmo: string | number
  cycle: number
}

export interface TrajectoryBuffers {
  positions: Float32Array
  colors: Float32Array
}

const EARTH_RADIUS_M = 6_371_000
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export function toGlobePosition(longitude: number, latitude: number, depthM: number, exaggeration: number): [number, number, number] {
  if (!finite(longitude) || longitude < -180 || longitude > 180) throw new RangeError('longitude must be between -180 and 180')
  if (!finite(latitude) || latitude < -90 || latitude > 90) throw new RangeError('latitude must be between -90 and 90')
  if (!finite(depthM) || depthM < 0) throw new RangeError('depth_m must be a non-negative finite number')
  if (!finite(exaggeration) || exaggeration < 0) throw new RangeError('exaggeration must be a non-negative finite number')
  const radius = Math.max(0, 1 - (depthM * exaggeration) / EARTH_RADIUS_M)
  const longitudeRadians = longitude * Math.PI / 180
  const latitudeRadians = latitude * Math.PI / 180
  const x = radius * Math.cos(latitudeRadians) * Math.cos(longitudeRadians)
  const y = radius * Math.sin(latitudeRadians)
  const z = radius * Math.cos(latitudeRadians) * Math.sin(longitudeRadians)
  return [Math.abs(x) < 1e-12 ? 0 : x, Math.abs(y) < 1e-12 ? 0 : y, Math.abs(z) < 1e-12 ? 0 : z]
}

export function isTrajectoryRow(row: Record<string, unknown>): row is Record<string, unknown> & TrajectoryRow {
  return finite(row.longitude) && row.longitude >= -180 && row.longitude <= 180 && finite(row.latitude) && row.latitude >= -90 && row.latitude <= 90 && finite(row.depth_m) && row.depth_m >= 0 && typeof row.timestamp === 'string' && !Number.isNaN(Date.parse(row.timestamp)) && (typeof row.wmo === 'string' || finite(row.wmo)) && finite(row.cycle)
}

export function buildTrajectoryBuffers(rows: readonly TrajectoryRow[], exaggeration: number): TrajectoryBuffers {
  const positions = new Float32Array(rows.length * 3)
  const colors = new Float32Array(rows.length * 3)
  const times = rows.map((row) => Date.parse(row.timestamp))
  const start = Math.min(...times)
  const span = Math.max(...times) - start || 1
  rows.forEach((row, index) => {
    positions.set(toGlobePosition(row.longitude, row.latitude, row.depth_m, exaggeration), index * 3)
    const t = (times[index] - start) / span
    colors.set([0.04 + t * 0.4, 0.34 + t * 0.36, 0.46 + (1 - t) * 0.32], index * 3)
  })
  return { positions, colors }
}
