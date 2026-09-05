import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { exportEvidence } from '../lib/api'
import { ScientificReceipt } from './ScientificReceipt'

vi.mock('../lib/api', () => ({ exportEvidence: vi.fn() }))

const result = (wmo: string, cycle: number, source_profile_index: number) => ({
  query_plan: { operation: 'find_profiles' as const, bbox: [60, 0, 80, 20] as [number, number, number, number], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP'] as ('TEMP')[], qc_mode: 'research' as const, row_limit: 100 },
  data: [{ wmo, cycle, source_profile_index, vertical_sampling_scheme: 'primary' }],
  chart_spec: [], provenance: [], qc_summary: { retained: 1, rejected: 0 }, methods: [], assumptions: [], warnings: [],
})

test('replaces export selections when the successful representation set changes', async () => {
  vi.mocked(exportEvidence).mockResolvedValue(new Blob())
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:test', revokeObjectURL: () => undefined })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  const { rerender } = render(<ScientificReceipt result={result('1900001', 7, 0)} />)

  rerender(<ScientificReceipt result={result('1900002', 8, 1)} />)
  fireEvent.click(screen.getByRole('button', { name: 'Download evidence ZIP' }))

  await waitFor(() => expect(exportEvidence).toHaveBeenCalledWith(expect.anything(), [{ wmo: '1900002', cycle: 8, source_profile_index: 1 }]))
})
