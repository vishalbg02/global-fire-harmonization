import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import App from './App.tsx'

describe('App shell', () => {
  it('renders the project heading and the placeholder statement', () => {
    const html = renderToString(<App />)
    expect(html).toContain('Global Fire Harmonization')
    expect(html).toContain('Application shell only')
  })

  it('shows no data values', () => {
    const html = renderToString(<App />)
    expect(html).not.toMatch(/\d+%/)
  })
})
