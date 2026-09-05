import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { deriveSection, executeQuery, interpretQuestion } from '../lib/api'
import { InvestigationWorkspace } from './InvestigationWorkspace'

vi.mock('../lib/api', () => ({ ApiError: class ApiError extends Error {}, executeQuery: vi.fn(), interpretQuestion: vi.fn(), deriveSection: vi.fn(), exportEvidence: vi.fn() }))

const row = (wmo: string, cycle: number, source_profile_index: number) => ({ wmo, cycle, source_profile_index, vertical_sampling_scheme: 'primary', depth_m: 10, latitude: 10, longitude: 70, timestamp: '2023-03-15T00:00:00Z', temperature_raw: 28, salinity_raw: 34, conservative_temperature: 27.9, absolute_salinity: 34.01 })
const response = {
  query_plan: { operation: 'find_profiles' as const, bbox: [60, 0, 80, 20] as [number, number, number, number], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP', 'PSAL'] as ('TEMP' | 'PSAL')[], qc_mode: 'research' as const, row_limit: 10000 },
  data: [row('1900001', 7, 0), row('1900002', 8, 0), row('1900003', 9, 0)],
  chart_spec: [{ profile_metrics: [{ wmo: '1900001', cycle: 7, source_profile_index: 0, name: 'principal thermocline', value: -0.2, depth_m: 50, units: 'degC m-1', uncertainty_m: 10, algorithm: 'three_level', parameters: { adjusted_error_max: 0.1 }, quality_label: 'research QC 1' }] }],
  provenance: [{ source_url: 'https://example.test/a.nc', snapshot_doi: '10.1234/nereid', fetched_at: '2023-03-26T00:00:00Z', sha256: 'a'.repeat(64) }], qc_summary: { retained: 3, rejected: 2 }, methods: [{ name: 'duckdb_parameterized_profile_query', version: '1', parameters: {} }], assumptions: [], warnings: [], answer: null,
}
const section = { ...response, data: [{ observation_coordinates: [{ wmo: '1900001', cycle: 7 }, { wmo: '1900002', cycle: 8 }], section_cells: [{ left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: null }], masked_gaps: [{ reason: 'time_gap' }] }], chart_spec: [] }
const mockedExecuteQuery = vi.mocked(executeQuery)
const mockedInterpretQuestion = vi.mocked(interpretQuestion)
const mockedDeriveSection = vi.mocked(deriveSection)
afterEach(() => { cleanup(); vi.resetAllMocks() })

test('links exactly two default representations across plots and metric refusals', async () => {
  mockedExecuteQuery.mockResolvedValue(response)
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByRole('img', { name: /1900001 cycle 7 representation 0: Conservative Temperature/ })
  expect(screen.getAllByRole('img', { name: /Conservative Temperature/ })).toHaveLength(2)
  expect(screen.queryByRole('img', { name: /1900003 cycle 9/ })).toBeNull()
  expect(screen.getByText(/-0.2 degC m-1 at 50 m/)).toBeDefined()
  expect(screen.getAllByText(/Insufficient evidence for/).length).toBeGreaterThan(0)
  fireEvent.click(screen.getByRole('radio', { name: 'Raw observations' }))
  expect(screen.getAllByRole('img', { name: /in-situ Temperature \(degC\) and Practical Salinity \(PSS-78, unitless\)/ })).toHaveLength(2)
})

test('resets selection only after a successful replacement result', async () => {
  mockedExecuteQuery.mockResolvedValueOnce(response).mockResolvedValueOnce({ ...response, data: [row('1900010', 10, 0), row('1900011', 11, 0)] })
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByLabelText(/1900001 \/ cycle 7 \/ representation 0/)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByLabelText(/1900010 \/ cycle 10 \/ representation 0/)
  expect(screen.queryByLabelText(/1900001 \/ cycle 7/)).toBeNull()
})

test('derives a section with the same exact selected IDs and retains prior data on refusal', async () => {
  mockedDeriveSection.mockResolvedValueOnce(section).mockRejectedValueOnce(new Error('refused'))
  render(<InvestigationWorkspace initialResult={response} />)
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await screen.findByRole('table', { name: 'Cross-section observations' })
  expect(mockedDeriveSection).toHaveBeenCalledWith(expect.objectContaining({ profile_ids: [{ wmo: '1900001', cycle: 7, source_profile_index: 0 }, { wmo: '1900002', cycle: 8, source_profile_index: 0 }] }), expect.anything())
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await screen.findByRole('alert')
  expect(screen.getByRole('table', { name: 'Cross-section observations' })).toBeDefined()
})

test('selection changes abort and invalidate an in-flight section', async () => {
  let resolveSection: (value: typeof section) => void = () => undefined
  mockedDeriveSection.mockImplementationOnce((_request, signal) => new Promise((resolve) => { resolveSection = resolve; expect(signal).toBeDefined() }))
  render(<InvestigationWorkspace initialResult={response} />)
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await waitFor(() => expect(mockedDeriveSection).toHaveBeenCalledTimes(1))
  const signal = mockedDeriveSection.mock.calls[0][1]!
  fireEvent.click(screen.getByLabelText(/1900003 \/ cycle 9 \/ representation 0/))
  expect(signal.aborted).toBe(true)
  resolveSection(section)
  await waitFor(() => expect(screen.queryByRole('table', { name: 'Cross-section observations' })).toBeNull())
})

test('a replacement query invalidates an older section response', async () => {
  let resolveSection: (value: typeof section) => void = () => undefined
  let resolveQuery: (value: typeof response) => void = () => undefined
  mockedDeriveSection.mockImplementationOnce(() => new Promise((resolve) => { resolveSection = resolve }))
  mockedExecuteQuery.mockImplementationOnce(() => new Promise((resolve) => { resolveQuery = resolve }))
  render(<InvestigationWorkspace initialResult={response} />)
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await waitFor(() => expect(mockedDeriveSection).toHaveBeenCalledTimes(1))
  const signal = mockedDeriveSection.mock.calls[0][1]!
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  expect(signal.aborted).toBe(true)
  resolveSection(section)
  resolveQuery({ ...response, data: [row('1900010', 10, 0), row('1900011', 11, 0)] })
  await screen.findByLabelText(/1900010 \/ cycle 10 \/ representation 0/)
  expect(screen.queryByRole('table', { name: 'Cross-section observations' })).toBeNull()
})

test('shows that explicit filters still work when AI interpretation is unavailable', async () => {
  mockedInterpretQuestion.mockResolvedValue({ plan: null, planner: 'explicit', warnings: ['AI interpretation unavailable—filters still work. Use explicit filters.'] })
  render(<InvestigationWorkspace />)
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Find profiles near 10N' } })
  fireEvent.click(screen.getByRole('button', { name: 'Interpret question' }))
  expect((await screen.findByRole('status')).textContent).toContain('AI interpretation unavailable—filters still work')
})

test('does not let a superseded request replace the newer result', async () => {
  let resolveOld: (value: typeof response) => void = () => undefined; let resolveNew: (value: typeof response) => void = () => undefined
  mockedExecuteQuery.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve })).mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve }))
  const { container } = render(<InvestigationWorkspace />)
  fireEvent.submit(container.querySelector('form')!); fireEvent.submit(container.querySelector('form')!)
  resolveNew({ ...response, data: [row('1900002', 8, 0)] }); await screen.findAllByText(/1900002 \/ cycle 8 \/ representation 0/)
  resolveOld(response); await waitFor(() => expect(screen.queryByText(/1900001 \/ cycle 7 \/ representation 0/)).toBeNull())
})
