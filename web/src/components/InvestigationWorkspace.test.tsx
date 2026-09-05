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

test('does not let a superseded request replace the newer result', async () => {
  let resolveOld: (value: typeof response) => void = () => undefined
  let resolveNew: (value: typeof response) => void = () => undefined
  mockedExecuteQuery
    .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve }))
  const { container } = render(<InvestigationWorkspace />)

  fireEvent.submit(container.querySelector('form')!)
  fireEvent.submit(container.querySelector('form')!)
  resolveNew({ ...response, data: [{ ...response.data[0], wmo: '1900002', cycle: 8 }] })
  await screen.findByText('1900002 / cycle 8')
  resolveOld(response)
  await waitFor(() => expect(screen.queryByText('1900001 / cycle 7')).toBeNull())
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

test('exposes masked section cells at their truthful profile and depth positions', () => {
  render(<InvestigationWorkspace initialResult={{
    ...response,
    data: [{
      observation_coordinates: [{ wmo: '1900001', cycle: 7, latitude: 10, longitude: 70, timestamp: '2023-03-15T00:00:00Z' }, { wmo: '1900002', cycle: 8, latitude: 11, longitude: 71, timestamp: '2023-03-16T00:00:00Z' }, { wmo: '1900003', cycle: 9, latitude: 12, longitude: 72, timestamp: '2023-03-17T00:00:00Z' }],
      section_cells: [{ left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: null }, { left_profile_index: 1, right_profile_index: 2, depth_m: 20, temperature: 24.5, salinity: 34.2 }],
      masked_gaps: [{ left_profile_index: 0, right_profile_index: 1, reason: 'time_gap' }],
    }],
  }} />)
  expect(screen.getByRole('table', { name: 'Cross-section observations' })).toBeDefined()
  expect(screen.getAllByText('masked').length).toBeGreaterThan(0)
  expect(screen.getByText('time gap')).toBeDefined()
  const cells = document.querySelectorAll('svg rect')
  expect(cells[0].getAttribute('x')).not.toBe(cells[1].getAttribute('x'))
  expect(cells[0].getAttribute('y')).not.toBe(cells[1].getAttribute('y'))
})

test('displays full provenance and all method parameters', () => {
  render(<InvestigationWorkspace initialResult={{
    ...response,
    provenance: [{ ...response.provenance[0], fetched_at: '2023-03-26T12:34:56.789Z', sha256: '0123456789abcdef'.repeat(4) }],
    methods: [{ name: 'gap_masked_linear_section', version: '1', parameters: { depth_step_m: 5, max_distance_km: 100 } }],
  }} />)
  expect(screen.getByText('2023-03-26T12:34:56.789Z')).toBeDefined()
  expect(screen.getByText('0123456789abcdef'.repeat(4))).toBeDefined()
  expect(screen.getByText('depth_step_m')).toBeDefined()
  expect(screen.getByText('5')).toBeDefined()
  expect(screen.getByText('max_distance_km')).toBeDefined()
  expect(screen.getByText('100')).toBeDefined()
})
