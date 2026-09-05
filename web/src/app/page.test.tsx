import { render, screen } from '@testing-library/react'
import Page from './page'

it('identifies the investigation workspace', () => {
  render(<Page />)
  expect(screen.getByRole('heading', { name: 'Nereid Ocean Investigation' })).toBeDefined()
})
