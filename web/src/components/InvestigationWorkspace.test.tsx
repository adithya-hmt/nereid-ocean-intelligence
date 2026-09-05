import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { deriveSection, executeQuery, interpretQuestion, type PlannerResponse } from '../lib/api'
import { CrossSectionPlot } from './CrossSectionPlot'
import { InvestigationWorkspace } from './InvestigationWorkspace'
import type { ResultEnvelope } from '../lib/types'

vi.mock('../lib/api', () => ({ ApiError: class ApiError extends Error {}, executeQuery: vi.fn(), interpretQuestion: vi.fn(), deriveSection: vi.fn(), exportEvidence: vi.fn() }))

const row = (wmo: string, cycle: number, source_profile_index: number) => ({ wmo, cycle, direction: 'A' as const, source_profile_index, vertical_sampling_scheme: 'primary', depth_m: 10, latitude: 10, longitude: 70, timestamp: '2023-03-15T00:00:00Z', temperature_raw: 28, salinity_raw: 34, conservative_temperature: 27.9, absolute_salinity: 34.01 })
const response: ResultEnvelope = {
  query_plan: { operation: 'find_profiles' as const, bbox: [60, 0, 80, 20] as [number, number, number, number], start_date: '2023-03-01', end_date: '2023-03-31', parameters: ['TEMP', 'PSAL'] as ('TEMP' | 'PSAL')[], qc_mode: 'research' as const, row_limit: 10000 },
  data: [row('1900001', 7, 0), row('1900002', 8, 0), row('1900003', 9, 0)],
  chart_spec: [{ profile_metrics: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0, name: 'principal_thermocline', value: -0.2, depth_m: 50, units: 'degC m-1', uncertainty_m: 10, algorithm: 'three_level', parameters: { adjusted_error_max: 0.1 }, quality_label: 'research QC 1' }] }],
  provenance: [{ source_url: 'https://example.test/a.nc', snapshot_doi: '10.1234/nereid', fetched_at: '2023-03-26T00:00:00Z', sha256: 'a'.repeat(64) }], qc_summary: { retained: 3, rejected: 2 }, methods: [{ name: 'duckdb_parameterized_profile_query', version: '1', parameters: {} }], assumptions: [], warnings: [], answer: null,
}
const coordinate = (wmo: string, cycle: number, source_profile_index: number, vertical_sampling_scheme: string, latitude: number, longitude: number, timestamp: string) => ({ wmo, cycle, direction: 'A' as const, source_profile_index, vertical_sampling_scheme, latitude, longitude, timestamp })
const section: ResultEnvelope = { ...response, data: [{ observation_coordinates: [coordinate('1900001', 7, 0, 'primary', 10, 70, '2023-03-15T00:00:00Z'), coordinate('1900002', 8, 0, 'primary', 11, 71, '2023-03-16T00:00:00Z')], section_cells: [{ left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: null }], masked_gaps: [{ left_profile_index: 0, right_profile_index: 1, reason: 'time_gap' }] }], chart_spec: [] }
const mockedExecuteQuery = vi.mocked(executeQuery)
const mockedInterpretQuestion = vi.mocked(interpretQuestion)
const mockedDeriveSection = vi.mocked(deriveSection)
afterEach(() => { cleanup(); vi.resetAllMocks() })

test('links exactly two default representations across plots and metric refusals', async () => {
  mockedExecuteQuery.mockResolvedValue(response)
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByRole('img', { name: /1900001 cycle 7 direction A representation 0: Conservative Temperature/ })
  expect(screen.getAllByRole('img', { name: /Conservative Temperature/ })).toHaveLength(2)
  expect(screen.queryByRole('img', { name: /1900003 cycle 9/ })).toBeNull()
  expect(screen.getByText(/-0.2 degC m-1 at 50 m/)).toBeDefined()
  expect(screen.getByText('Principal thermocline')).toBeDefined()
  expect(screen.getAllByText(/Insufficient evidence for/).length).toBeGreaterThan(0)
  fireEvent.click(screen.getByRole('radio', { name: 'Raw observations' }))
  expect(screen.getAllByRole('img', { name: /in-situ Temperature \(degC\) and Practical Salinity \(PSS-78, unitless\)/ })).toHaveLength(2)
})

test('empty parameters render both canonical metric slots', async () => {
  render(<InvestigationWorkspace initialResult={{ ...response, query_plan: { ...response.query_plan, parameters: [] } }} />)
  expect(screen.getByText('Principal thermocline')).toBeDefined()
  expect(screen.getAllByText(/Strongest salinity gradient/).length).toBeGreaterThan(0)
})

test('resets selection only after a successful replacement result', async () => {
  mockedExecuteQuery.mockResolvedValueOnce(response).mockResolvedValueOnce({ ...response, data: [row('1900010', 10, 0), row('1900011', 11, 0)] })
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByLabelText(/1900001 \/ cycle 7 \/ A \/ representation 0/)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByLabelText(/1900010 \/ cycle 10 \/ A \/ representation 0/)
  expect(screen.queryByLabelText(/1900001 \/ cycle 7/)).toBeNull()
})

test('derives a section with the same exact selected IDs and retains prior data on refusal', async () => {
  mockedDeriveSection.mockResolvedValueOnce(section).mockRejectedValueOnce(new Error('refused'))
  render(<InvestigationWorkspace initialResult={response} />)
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await screen.findByRole('table', { name: 'Cross-section observations' })
  expect(mockedDeriveSection).toHaveBeenCalledWith(expect.objectContaining({ profile_ids: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0 }, { wmo: '1900002', cycle: 8, direction: 'A', source_profile_index: 0 }] }), expect.anything())
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
  fireEvent.click(screen.getByLabelText(/1900003 \/ cycle 9 \/ A \/ representation 0/))
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
  await screen.findByLabelText(/1900010 \/ cycle 10 \/ A \/ representation 0/)
  expect(screen.queryByRole('table', { name: 'Cross-section observations' })).toBeNull()
})

test('uses each gap reason and exact representations in the section alternatives', () => {
  const multiGapSection: ResultEnvelope = {
    ...section,
    data: [{
      observation_coordinates: [
        coordinate('1900001', 7, 0, 'primary', 10, 70, '2023-03-15T00:00:00Z'),
        coordinate('1900001', 7, 1, 'secondary', 10.1, 70.1, '2023-03-16T00:00:00Z'),
        coordinate('1900002', 8, 0, 'primary', 11, 71, '2023-03-17T00:00:00Z'),
      ],
      section_cells: [
        { left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: null },
        { left_profile_index: 1, right_profile_index: 2, depth_m: 10, temperature: null, salinity: null },
        { left_profile_index: 0, right_profile_index: 1, depth_m: 20, temperature: 25, salinity: 34 },
      ],
      masked_gaps: [
        { left_profile_index: 0, right_profile_index: 1, reason: 'time_gap' },
        { left_profile_index: 1, right_profile_index: 2, reason: 'distance_gap' },
      ],
    }],
  }
  render(<CrossSectionPlot result={multiGapSection} />)
  expect(screen.getByText(/Observed coordinate: 1900001 \/ cycle 7 \/ A \/ representation 0 \/ primary/)).toBeDefined()
  expect(screen.getByText(/Observed coordinate: 1900001 \/ cycle 7 \/ A \/ representation 1 \/ secondary/)).toBeDefined()
  expect(screen.getByRole('table', { name: 'Cross-section observations' }).textContent).toContain('time gap')
  expect(screen.getByRole('table', { name: 'Cross-section observations' }).textContent).toContain('distance gap')
  expect(screen.getByRole('table', { name: 'Cross-section observations' }).textContent).toContain('interpolated derived')
  expect(screen.getByRole('table', { name: 'Cross-section observations' }).textContent).not.toContain('observed')
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
  resolveNew({ ...response, data: [row('1900002', 8, 0)] }); await screen.findAllByText(/1900002 \/ cycle 8 \/ A \/ representation 0/)
  resolveOld(response); await waitFor(() => expect(screen.queryByText(/1900001 \/ cycle 7 \/ A \/ representation 0/)).toBeNull())
})

test('a plan edit aborts a pending execution and clears its loading state', async () => {
  let resolveExecution: (value: typeof response) => void = () => undefined
  mockedExecuteQuery.mockImplementationOnce((_plan, signal) => new Promise((resolve) => { resolveExecution = resolve; expect(signal).toBeDefined() }))
  render(<InvestigationWorkspace />)
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await waitFor(() => expect(mockedExecuteQuery).toHaveBeenCalledTimes(1))
  const signal = mockedExecuteQuery.mock.calls[0][1]!
  fireEvent.change(screen.getByLabelText('Row limit'), { target: { value: '9' } })
  expect(signal.aborted).toBe(true)
  expect(screen.getByRole('button', { name: 'Run investigation' })).toBeDefined()
  resolveExecution(response)
  await waitFor(() => expect(screen.queryByLabelText(/1900001 \/ cycle 7/)).toBeNull())
})

test('a question edit aborts a pending planner and discards its plan and warning', async () => {
  let resolvePlanner: (value: PlannerResponse) => void = () => undefined
  mockedInterpretQuestion.mockImplementationOnce(() => new Promise((resolve) => { resolvePlanner = resolve }))
  render(<InvestigationWorkspace />)
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Find profiles' } })
  fireEvent.click(screen.getByRole('button', { name: 'Interpret question' }))
  await waitFor(() => expect(mockedInterpretQuestion).toHaveBeenCalledTimes(1))
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Find other profiles' } })
  expect(screen.getByRole('button', { name: 'Interpret question' })).toBeDefined()
  resolvePlanner({ plan: { ...response.query_plan, row_limit: 9 }, planner: 'azure', warnings: ['stale warning'] })
  await waitFor(() => expect(screen.queryByText('stale warning')).toBeNull())
  expect((screen.getByLabelText('Row limit') as HTMLInputElement).value).toBe('10000')
})

test('a successful planner response applies its plan and exits planning', async () => {
  let resolvePlanner: (value: PlannerResponse) => void = () => undefined
  mockedInterpretQuestion.mockImplementationOnce(() => new Promise((resolve) => { resolvePlanner = resolve }))
  render(<InvestigationWorkspace />)
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Find profiles' } })
  fireEvent.click(screen.getByRole('button', { name: 'Interpret question' }))
  await waitFor(() => expect(mockedInterpretQuestion).toHaveBeenCalledTimes(1))
  resolvePlanner({ plan: { ...response.query_plan, row_limit: 9 }, planner: 'azure', warnings: [] })
  await waitFor(() => expect((screen.getByLabelText('Row limit') as HTMLInputElement).value).toBe('9'))
  expect(screen.getByRole('button', { name: 'Interpret question' })).toBeDefined()
})

test('a stale planner cannot replace a later explicit execution', async () => {
  let resolvePlanner: (value: PlannerResponse) => void = () => undefined
  mockedInterpretQuestion.mockImplementationOnce(() => new Promise((resolve) => { resolvePlanner = resolve }))
  mockedExecuteQuery.mockResolvedValue({ ...response, data: [row('1900099', 99, 0)] })
  render(<InvestigationWorkspace />)
  fireEvent.change(screen.getByLabelText('Question (optional)'), { target: { value: 'Find profiles' } })
  fireEvent.click(screen.getByRole('button', { name: 'Interpret question' }))
  await waitFor(() => expect(mockedInterpretQuestion).toHaveBeenCalledTimes(1))
  const plannerSignal = mockedInterpretQuestion.mock.calls[0][1]!
  fireEvent.click(screen.getByRole('button', { name: 'Run investigation' }))
  await screen.findByLabelText(/1900099 \/ cycle 99 \/ A \/ representation 0/)
  expect(plannerSignal.aborted).toBe(true)
  resolvePlanner({ plan: { ...response.query_plan, row_limit: 9 }, planner: 'azure', warnings: ['stale warning'] })
  await waitFor(() => expect(screen.queryByText('stale warning')).toBeNull())
  expect((screen.getByLabelText('Row limit') as HTMLInputElement).value).toBe('10000')
  expect(screen.getByRole('button', { name: 'Interpret question' })).toBeDefined()
})

test('a PSAL-only section remains visible without temperature output', () => {
  render(<CrossSectionPlot result={{ ...section, query_plan: { ...section.query_plan, operation: 'derive_section', parameters: ['PSAL'] }, section_request: { profile_ids: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0 }, { wmo: '1900002', cycle: 8, direction: 'A', source_profile_index: 0 }], qc_mode: 'research', parameters: ['PSAL'], row_limit: 10000, depth_step_m: 10, max_time_gap_hours: 168, max_distance_km: 500, max_vertical_gap_m: 100 }, data: [{ ...section.data[0], section_cells: [{ left_profile_index: 0, right_profile_index: 1, depth_m: 10, temperature: null, salinity: 34.01 }] }] }} />)
  expect(screen.getByRole('img', { name: 'Gap-masked salinity cross-section' })).toBeDefined()
  expect(screen.getByRole('columnheader', { name: 'Salinity' })).toBeDefined()
  expect(screen.queryByRole('columnheader', { name: 'Temperature' })).toBeNull()
  expect(screen.getByRole('table', { name: 'Cross-section observations' }).textContent).toContain('34.010 g kg⁻¹')
})

test('a direct section renders its read-only receipt without profile or trajectory fallbacks', () => {
  render(<InvestigationWorkspace initialResult={{ ...section, query_plan: { ...section.query_plan, operation: 'derive_section', profile_ids: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0 }, { wmo: '1900002', cycle: 8, direction: 'A', source_profile_index: 0 }] }, section_request: { profile_ids: [{ wmo: '1900001', cycle: 7, direction: 'A', source_profile_index: 0 }, { wmo: '1900002', cycle: 8, direction: 'A', source_profile_index: 0 }], qc_mode: 'research', parameters: ['TEMP', 'PSAL'], row_limit: 10000, depth_step_m: 10, max_time_gap_hours: 168, max_distance_km: 500, max_vertical_gap_m: 100 } }} />)
  expect(screen.getByRole('table', { name: 'Cross-section observations' })).toBeDefined()
  expect(screen.queryByText(/returned observations have no complete/)).toBeNull()
  expect(screen.queryByText('Derived cross-section')).toBeNull()
  expect(screen.getByText('Scientific receipt')).toBeDefined()
  expect(screen.getByText('Sources')).toBeDefined()
  expect(screen.getByText('Methods')).toBeDefined()
  expect(screen.getByText('Assumptions & warnings')).toBeDefined()
  expect(screen.queryByText('Select exact profile representations for linked views and evidence export')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Download evidence ZIP' })).toBeNull()
})

test('forwards all linked section controls, row limit, and effective parameters', async () => {
  mockedDeriveSection.mockResolvedValue(section)
  render(<InvestigationWorkspace initialResult={{ ...response, query_plan: { ...response.query_plan, parameters: ['TEMP'], row_limit: 77 } }} />)
  for (const [label, value] of [['Depth step (m)', '11'], ['Maximum time gap (hours)', '22'], ['Maximum distance (km)', '33'], ['Maximum vertical gap (m)', '44']] as const) fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Derive section from selected representations' }))
  await waitFor(() => expect(mockedDeriveSection).toHaveBeenCalledWith(expect.objectContaining({ parameters: ['TEMP'], row_limit: 77, depth_step_m: 11, max_time_gap_hours: 22, max_distance_km: 33, max_vertical_gap_m: 44 }), expect.anything()))
  render(<InvestigationWorkspace initialResult={{ ...response, query_plan: { ...response.query_plan, parameters: ['PRES'] } }} />)
  expect(screen.getAllByRole('status').at(-1)?.textContent).toContain('requires requested TEMP and/or PSAL')
  expect(screen.getAllByRole('button', { name: 'Derive section from selected representations' }).at(-1)?.hasAttribute('disabled')).toBe(true)
})
