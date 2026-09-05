import { describe, expect, it } from 'vitest'

import { rowsAtOrBefore, sortedUniqueTimestamps } from './trajectory'

const rows = [
  { longitude: 2, latitude: 2, depth_m: 20, timestamp: '2023-03-02T00:00:00Z', wmo: '1', cycle: 2 },
  { longitude: 1, latitude: 1, depth_m: 10, timestamp: '2023-03-01T00:00:00Z', wmo: '1', cycle: 1 },
  { longitude: 1, latitude: 1, depth_m: 30, timestamp: '2023-03-01T00:00:00Z', wmo: '1', cycle: 1 },
]

describe('trajectory time selection', () => {
  it('sorts and deduplicates parsed timestamps from unsorted source rows', () => {
    expect(sortedUniqueTimestamps(rows)).toEqual(['2023-03-01T00:00:00.000Z', '2023-03-02T00:00:00.000Z'])
  })

  it('filters immutable source rows by cutoff without splitting same-timestamp depths', () => {
    const selected = rowsAtOrBefore(rows, '2023-03-01T00:00:00.000Z')
    expect(selected).toHaveLength(2)
    expect(selected.map((row) => row.depth_m)).toEqual([10, 30])
    expect(rows).toHaveLength(3)
  })
})
