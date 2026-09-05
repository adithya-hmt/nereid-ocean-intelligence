import type { TrajectoryRow } from './geometry'

export function sortedUniqueTimestamps(rows: readonly TrajectoryRow[]): string[] {
  return Array.from(new Set(rows.map((row) => Date.parse(row.timestamp)))).sort((left, right) => left - right).map((timestamp) => new Date(timestamp).toISOString())
}

export function rowsAtOrBefore(rows: readonly TrajectoryRow[], cutoff: string): TrajectoryRow[] {
  const cutoffTime = Date.parse(cutoff)
  return rows.filter((row) => Date.parse(row.timestamp) <= cutoffTime)
}
