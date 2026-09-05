import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

vi.mock('../components/TrajectoryGlobe', () => ({ TrajectoryGlobe: ({ benchmark }: { benchmark?: boolean }) => <p>{benchmark ? 'Benchmark only — synthetic rows are never scientific results.' : 'Trajectory globe'}</p> }))

import Page from './page'

it('identifies the investigation workspace', async () => {
  render(await Page({ searchParams: Promise.resolve({}) }))
  expect(screen.getByRole('heading', { name: 'Nereid Ocean Investigation' })).toBeDefined()
})

it('forwards the benchmark query to the workspace', async () => {
  const page = await Page({ searchParams: Promise.resolve({ benchmark: '100000' }) })
  render(page)
  expect(screen.getByText('Benchmark only — synthetic rows are never scientific results.')).toBeDefined()
})
