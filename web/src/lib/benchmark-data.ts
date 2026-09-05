import type { TrajectoryRow } from './geometry'

export const BENCHMARK_ONLY_LABEL = 'Benchmark only — synthetic rows are never scientific results.'

export function createBenchmarkRows(count: number): TrajectoryRow[] {
  if (!Number.isSafeInteger(count) || count < 1 || count > 100_000) throw new RangeError('benchmark count must be between 1 and 100000')
  let state = 0x4e455245
  const next = () => {
    state = (Math.imul(state, 1_664_525) + 1_013_904_223) >>> 0
    return state / 0x1_0000_0000
  }
  const start = Date.parse('2023-03-01T00:00:00Z')
  return Array.from({ length: count }, (_, index) => ({
    longitude: next() * 360 - 180,
    latitude: next() * 160 - 80,
    depth_m: next() * 6000,
    timestamp: new Date(start + index * 60_000).toISOString(),
    wmo: `BENCH-${Math.floor(index / 1000)}`,
    cycle: index % 1000,
  }))
}
