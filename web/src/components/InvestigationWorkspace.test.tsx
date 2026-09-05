import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { executeQuery } from '../lib/api'
import { InvestigationWorkspace } from './InvestigationWorkspace'

vi.mock('../lib/api', () => ({ executeQuery: vi.fn() }))

const response = {
  query_plan: {
    operation: 'find_profiles' as const,
    bbox: [60, 0, 80, 20] as [number, number, number, number],
    start_date: '2023-03-01',
    end_date: '2023-03-31',
    parameters: ['TEMP', 'PSAL'] as ('TEMP' | 'PSAL')[],
    qc_mode: 'research' as const,
    row_limit: 10000,
  },
  data: [{
    wmo: '1900001', cycle: 7, depth_m: 10, latitude: 10, longitude: 70,
    timestamp: '2023-03-15T00:00:00Z', temperature_raw: 28, temperature_best: 27.9,
    salinity_raw: 34, salinity_best: 34.01,
  }],
  chart_spec: [],
  provenance: [{ source_url: 'https://example.test/a.nc', snapshot_doi: '10.1234/nereid', fetched_at: '2023-03-26T00:00:00Z', sha256: 'a'.repeat(64) }],
  qc_summary: { retained: 1, rejected: 2 },
  methods: [{ name: 'duckdb_parameterized_profile_query', version: '1', parameters: {} }],
  assumptions: [], warnings: [], answer: null,
}

const mockedExecuteQuery = vi.mocked(executeQuery)

afterEach(() => { cleanup(); vi.resetAllMocks() })

test('executes the curated workflow and renders its scientific receipt', async () => {
  mockedExecuteQuery.mockResolvedValue(response)
  render(<InvestigationWorkspace />)

  fireEvent.click(screen.getByRole('button', { name: 'Use March 2023 example' }))
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))

  await waitFor(() => expect(screen.getByText(/10\.1234\/nereid/)).toBeDefined())
  expect(screen.getByText('60°E to 80°E · 0°N to 20°N')).toBeDefined()
  expect(screen.getByText('March 1, 2023 — March 31, 2023')).toBeDefined()
  expect(screen.getByText('Research')).toBeDefined()
  expect(screen.getByText('1900001 / cycle 7')).toBeDefined()
  expect(screen.getByText(/retained/)).toBeDefined()
  expect(screen.getByText(/excluded/)).toBeDefined()
  expect(screen.getByText('duckdb_parameterized_profile_query')).toBeDefined()
})

test('switches the profile plot between raw and best-adjusted observations', async () => {
  mockedExecuteQuery.mockResolvedValue(response)
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))

  await screen.findByLabelText('Temperature profile')
  expect(screen.getByText(/27\.90/)).toBeDefined()
  fireEvent.click(screen.getByRole('radio', { name: 'Raw observations' }))
  expect(screen.getByText(/28\.00/)).toBeDefined()
})

test('shows a non-destructive widening suggestion for no matches', async () => {
  mockedExecuteQuery.mockResolvedValue({ ...response, data: [], provenance: [], warnings: ['No matching profiles; widen one bounded filter.'] })
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))

  expect((await screen.findAllByText('No matching profiles; widen one bounded filter.')).length).toBeGreaterThan(0)
})

test('exposes masked section cells in an accessible table', () => {
  render(<InvestigationWorkspace initialResult={{
    ...response,
    data: [{
      observation_coordinates: [{ wmo: '1900001', cycle: 7, latitude: 10, longitude: 70, timestamp: '2023-03-15T00:00:00Z' }],
      section_cells: [{ left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: null }],
      masked_gaps: [{ left_profile_index: 0, right_profile_index: 1, reason: 'time_gap' }],
    }],
  }} />)
  expect(screen.getByRole('table', { name: 'Cross-section observations' })).toBeDefined()
  expect(screen.getAllByText('masked').length).toBeGreaterThan(0)
  expect(screen.getByText('time gap')).toBeDefined()
})
