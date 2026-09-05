import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { QueryControls } from './QueryControls'

const plan = { operation: 'find_profiles' as const, bbox: [60, 0, 80, 20] as [number, number, number, number], start_date: '2023-03-01', end_date: '2023-03-31', parameters: [], qc_mode: 'research' as const, row_limit: 10000 }

test('treats empty parameters as all parameters and removes only the clicked parameter', () => {
  const onChange = vi.fn()
  render(<QueryControls plan={plan} question="" loading={false} planning={false} onChange={onChange} onQuestionChange={vi.fn()} onInterpret={vi.fn()} onSubmit={vi.fn()} onExample={vi.fn()} />)

  expect((screen.getByRole('checkbox', { name: 'TEMP' }) as HTMLInputElement).checked).toBe(true)
  expect((screen.getByRole('checkbox', { name: 'PSAL' }) as HTMLInputElement).checked).toBe(true)
  expect((screen.getByRole('checkbox', { name: 'PRES' }) as HTMLInputElement).checked).toBe(true)
  fireEvent.click(screen.getByRole('checkbox', { name: 'TEMP' }))
  expect(onChange).toHaveBeenCalledWith({ ...plan, parameters: ['PSAL', 'PRES'] })
})
