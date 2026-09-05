import { describe, expect, it } from 'vitest'

import { buildTrajectoryBuffers, toGlobePosition } from './geometry'

describe('toGlobePosition', () => {
  it('maps cardinal longitude and latitude to unit-sphere axes', () => {
    expect(toGlobePosition(0, 0, 0, 1)).toEqual([1, 0, 0])
    expect(toGlobePosition(90, 0, 0, 1)[0]).toBeCloseTo(0)
    expect(toGlobePosition(90, 0, 0, 1)[2]).toBeCloseTo(1)
    expect(toGlobePosition(0, 90, 0, 1)).toEqual([0, 1, 0])
  })

  it('moves depth inward and exaggeration only changes radial depth', () => {
    const normal = toGlobePosition(45, 30, 1000, 1)
    const exaggerated = toGlobePosition(45, 30, 1000, 2)
    expect(Math.hypot(...normal)).toBeCloseTo(1 - 1000 / 6_371_000)
    expect(Math.hypot(...exaggerated)).toBeCloseTo(1 - 2000 / 6_371_000)
    normal.forEach((value, index) => expect(value / Math.hypot(...normal)).toBeCloseTo(exaggerated[index] / Math.hypot(...exaggerated)))
  })

  it('rejects invalid coordinates and depth', () => {
    expect(() => toGlobePosition(181, 0, 0, 1)).toThrow()
    expect(() => toGlobePosition(0, -91, 0, 1)).toThrow()
    expect(() => toGlobePosition(0, 0, -1, 1)).toThrow()
    expect(() => toGlobePosition(0, 0, Number.NaN, 1)).toThrow()
  })
})

describe('buildTrajectoryBuffers', () => {
  it('creates one position and color entry per valid source row without mutating it', () => {
    const rows = [
      { longitude: 70, latitude: 10, depth_m: 10, timestamp: '2023-03-01T00:00:00Z', wmo: '1', cycle: 1 },
      { longitude: 71, latitude: 11, depth_m: 20, timestamp: '2023-03-02T00:00:00Z', wmo: '1', cycle: 2 },
    ]
    const buffers = buildTrajectoryBuffers(rows, 1)
    expect(buffers.positions).toBeInstanceOf(Float32Array)
    expect(buffers.colors).toBeInstanceOf(Float32Array)
    expect(buffers.positions).toHaveLength(6)
    expect(buffers.colors).toHaveLength(6)
    expect(rows[0].depth_m).toBe(10)
  })
})
