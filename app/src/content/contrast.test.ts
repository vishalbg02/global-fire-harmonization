import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { contrastRatio, parseColor } from './colorVision.ts'

// WCAG 2.1 AA contrast of the colour tokens in src/styles/tokens.css (T-042, moved by T-070). The tokens are read from the
// stylesheet, so a change there is checked. The app has one (light) theme: `color-scheme: light`.
const css = readFileSync(new URL('../styles/tokens.css', import.meta.url), 'utf8')
const token = (name: string): string => {
  const m = new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{3,6})`).exec(css)
  if (m === null) throw new Error(`token --${name} not found`)
  return m[1] as string
}
const ratio = (fg: string, bg: string) => contrastRatio(parseColor(fg), parseColor(bg))

describe('contrast of the colour tokens (WCAG 2.1 AA)', () => {
  it('has a single light theme, so one set of tokens is checked', () => {
    expect(css).toContain('color-scheme: light')
    expect(css).not.toContain('prefers-color-scheme: dark')
  })

  it('text is at least 4.5:1 on the page and on the panels', () => {
    for (const fg of ['ink', 'muted']) {
      for (const bg of ['page', 'surface']) {
        expect(ratio(token(fg), token(bg)), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })

  it('the focus outline and the skip-link border are at least 3:1 against the page and the panels', () => {
    for (const bg of ['page', 'surface']) expect(ratio(token('focus'), token(bg))).toBeGreaterThanOrEqual(3)
  })

  it('the banner and note text pairs written in the stylesheet are at least 4.5:1', () => {
    expect(ratio(token('on-brand'), token('ink'))).toBeGreaterThanOrEqual(4.5) // synthetic banner
    expect(ratio(token('ink'), token('warn-bg'))).toBeGreaterThanOrEqual(4.5) // raw-only note and warning badges
    expect(ratio('#1b1b1f', '#e0e0e0')).toBeGreaterThanOrEqual(4.5) // no-data table cells
    expect(ratio(token('on-brand'), token('brand'))).toBeGreaterThanOrEqual(4.5) // header
    expect(ratio(token('on-brand-muted'), token('brand'))).toBeGreaterThanOrEqual(4.5) // header tagline
  })

  it('the verdict badge text is at least 4.5:1 on its tint', () => {
    for (const v of ['above', 'below', 'within', 'cannot', 'none']) {
      expect(ratio(token(`v-${v}-ink`), token(`v-${v}-tint`)), v).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('the verdict colours are the ones of the map, the only accent is vermillion, and there are no shadows or large radii', () => {
    expect(token('accent').toLowerCase()).toBe('#d55e00')
    expect(token('v-above').toLowerCase()).toBe('#d55e00')
    expect(token('v-below').toLowerCase()).toBe('#0072b2')
    expect(token('v-within').toLowerCase()).toBe('#999999')
    expect(token('v-cannot').toLowerCase()).toBe('#cccccc')
    const radius = /--radius:\s*(\d+)px/.exec(css)
    expect(Number(radius?.[1])).toBeLessThanOrEqual(4)
    for (const file of ['../index.css', '../styles/layout.css']) {
      expect(readFileSync(new URL(file, import.meta.url), 'utf8')).not.toMatch(/box-shadow:\s*(?!none)\S/)
    }
  })
})
