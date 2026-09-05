import { fireEvent, render, screen } from '@testing-library/react'
import { ProfilePlot } from './ProfilePlot'
import type { ResultEnvelope } from '../lib/types'

const result: ResultEnvelope = {
  query_plan: { operation: 'get_profile', wmo: '1900001', cycle: 7, direction: 'A', parameters: ['TEMP'], qc_mode: 'research', row_limit: 100 },
  data: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0, depth_m: 10, temperature_raw: null, conservative_temperature: 27.9, salinity_raw: null, absolute_salinity: null }],
  chart_spec: [], provenance: [], qc_summary: { retained: 1, rejected: 0 }, methods: [], assumptions: [], warnings: [],
}

test('raw QC quarantine omits a raw mismatch while retaining the adjusted TEOS observation', () => {
  render(<ProfilePlot result={result} selections={[{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0 }]} />)
  expect(screen.getByText('27.90')).toBeDefined()
  fireEvent.click(screen.getByLabelText('Raw observations'))
  expect(screen.queryByText('28.00')).toBeNull()
  expect(screen.getByRole('status').textContent).toContain('no requested observations')
})
