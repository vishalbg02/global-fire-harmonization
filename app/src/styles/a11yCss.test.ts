import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { contrastRatio, parseColor } from '../content/colorVision.ts'

// Stylesheet checks for the responsive and keyboard rules of T-074. SYNTHETIC: no data are involved.
const read = (file: string) => readFileSync(new URL(file, import.meta.url), 'utf8')
const tokens = read('./tokens.css')
const layout = read('./layout.css')
const phoneBlocks = layout.split('@media (max-width: 640px)').slice(1)

describe('focus styles (T-074)', () => {
  it('one outline rule covers links, buttons, fields, summaries and anything with a tabindex', () => {
    const rule = /([^{}]*)\{\s*outline: 2px solid var\(--focus\)/.exec(tokens)?.[1] ?? ''
    for (const sel of ['a:focus-visible', 'button:focus-visible', 'input:focus-visible', 'summary:focus-visible', '[tabindex]:focus-visible']) {
      expect(rule, sel).toContain(sel)
    }
  })

  it("the map's zoom buttons get the same outline instead of their own faint ring", () => {
    expect(tokens).toMatch(/\.maplibregl-ctrl button:focus-visible\s*\{[^}]*outline: 2px solid var\(--focus\)/)
  })

  it('the white focus ring on the navy header is at least 3:1', () => {
    const brand = /--brand:\s*(#[0-9a-fA-F]{6})/.exec(tokens)?.[1] as string
    expect(contrastRatio(parseColor('#ffffff'), parseColor(brand))).toBeGreaterThanOrEqual(3)
  })
})

describe('phone touch targets (T-074)', () => {
  const phone = phoneBlocks.join('\n')

  it('buttons, chips, tabs and header links are at least 44 px high', () => {
    for (const sel of ['.btn,', '.chip,', ".tabbar [role='tab']", '.top-link']) expect(phone, sel).toContain(sel)
    expect(phone).toMatch(/min-height: 44px/)
  })

  it('the segments, the area box and the month slider are 44 px', () => {
    expect(phone).toMatch(/\.seg-option span\s*\{[^}]*min-height: 44px/)
    expect(phone).toMatch(/input\[type='search'\][^{]*\{[^}]*min-height: 44px/)
    expect(phone).toMatch(/input\[type='range'\]\s*\{\s*height: 44px/)
  })

  it('checkboxes and radio buttons are at least 24 px (WCAG 2.2, 2.5.8)', () => {
    expect(layout).toMatch(/input\[type='checkbox'\][^{]*\{[^}]*width: 24px;\s*height: 24px/)
  })
})
