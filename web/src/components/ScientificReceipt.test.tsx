import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { vi } from 'vitest'

import { exportEvidence } from '../lib/api'
import type { ResultEnvelope } from '../lib/types'
import { ScientificReceipt } from './ScientificReceipt'

vi.mock('../lib/api', () => ({ exportEvidence: vi.fn() }))

const result = (wmo: string, cycle: number, source_profile_index: number) => ({
  query_plan: { operation: 'find_profiles' as const, bbox: [60, 0, 80, 20] as [number, number, number, number], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP'] as ('TEMP')[], qc_mode: 'research' as const, row_limit: 100 },
  data: [{ wmo, cycle, direction: 'A' as const, source_profile_index, vertical_sampling_scheme: 'primary' }], chart_spec: [], provenance: [], qc_summary: { retained: 1, rejected: 0 }, methods: [] as ResultEnvelope['methods'], assumptions: [], warnings: [],
})

function Receipt({ current }: { current: ReturnType<typeof result> }) {
  const [selected, setSelected] = useState([{ wmo: current.data[0].wmo, cycle: current.data[0].cycle, direction: 'A' as 'A' | 'D', source_profile_index: current.data[0].source_profile_index }])
  return <ScientificReceipt result={current} selections={selected} onSelectionChange={setSelected} />
}

test('exports the workspace-owned exact selections', async () => {
  vi.mocked(exportEvidence).mockResolvedValue(new Blob())
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: () => undefined })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  render(<Receipt current={result('1900002', 8, 1)} />)
  fireEvent.click(screen.getByRole('button', { name: 'Download evidence ZIP' }))
  await waitFor(() => expect(exportEvidence).toHaveBeenCalledWith(expect.anything(), [{ wmo: '1900002', cycle: 8, direction: 'A', source_profile_index: 1 }]))
})

test('renders method units as accessible receipt evidence', () => {
  render(<Receipt current={{ ...result('1900002', 8, 1), methods: [{ name: 'gap_masked_linear_section', version: '1', parameters: {}, units: { temperature: 'degC', salinity: 'g kg-1' } }] }} />)
  expect(screen.getByText('temperature units')).toBeDefined()
  expect(screen.getByText('degC')).toBeDefined()
  expect(screen.getByText('salinity units')).toBeDefined()
  expect(screen.getByText('g kg-1')).toBeDefined()
})

test('read-only section receipt exposes exact identities and request controls without export controls', () => {
  const section = { ...result('1900002', 8, 1), section_request: { profile_ids: [{ wmo: '1900002', cycle: 8, direction: 'A' as const, source_profile_index: 1 }, { wmo: '1900003', cycle: 9, direction: 'D' as const, source_profile_index: 0 }], qc_mode: 'research' as const, parameters: ['TEMP' as const], row_limit: 77, depth_step_m: 11, max_time_gap_hours: 22, max_distance_km: 33, max_vertical_gap_m: 44 } }
  render(<ScientificReceipt result={section} selections={[]} onSelectionChange={() => undefined} readOnly heading="Derived section receipt" headingId="derived-section-receipt-heading" />)
  expect(screen.getByRole('heading', { name: 'Derived section receipt' }).id).toBe('derived-section-receipt-heading')
  expect(screen.getByText(/1900002 \/ cycle 8 \/ A \/ representation 1/)).toBeDefined()
  expect(screen.getByText(/1900003 \/ cycle 9 \/ D \/ representation 0/)).toBeDefined()
  expect(screen.getByText('depth_step_m')).toBeDefined()
  expect(screen.getByText('11')).toBeDefined()
  expect(screen.queryByRole('button', { name: 'Download evidence ZIP' })).toBeNull()
  expect(screen.queryByRole('checkbox')).toBeNull()
})
