import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { DockIcon } from './DockIcon.tsx'
import { LONG_PRESS_MS, TIP_HOLD_MS } from './dockIcon.ts'

describe('compact dock icon buttons (T-093)', () => {
  it('are named by their visible label', () => {
    const html = renderToString(<DockIcon label="Layers" icon="layers" aria-expanded={false} />)
    const labelledBy = /aria-labelledby="([^"]+)"/.exec(html)?.[1]
    expect(labelledBy).toBeTruthy()
    expect(html).toContain(`id="${labelledBy}" class="dock-tip" data-shown="false">Layers</span>`)
    expect(html).not.toContain('aria-label=')
  })

  it('keep their state attributes and the tour anchor', () => {
    const html = renderToString(<DockIcon label="Satellite view" icon="satellite" role="switch" aria-checked data-tour="raw" disabled />)
    expect(html).toContain('role="switch"')
    expect(html).toContain('aria-checked="true"')
    expect(html).toContain('data-tour="raw"')
    expect(html).toContain('disabled=""')
  })

  it('draw the icon as decoration only', () => {
    const html = renderToString(<DockIcon label="Globe" icon="globe" aria-pressed />)
    expect(html).toMatch(/<svg[^>]*aria-hidden="true"/)
    expect(html).toContain('aria-pressed="true"')
  })

  it('show a long-press label for longer than the press itself', () => {
    expect(LONG_PRESS_MS).toBeGreaterThanOrEqual(400)
    expect(TIP_HOLD_MS).toBeGreaterThan(LONG_PRESS_MS)
  })
})
