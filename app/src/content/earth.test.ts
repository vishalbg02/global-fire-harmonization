import { describe, expect, it } from 'vitest'
import { EARTH_TEXTS, SIGNAL_RULE } from './earth.ts'

describe('Earth view sentences (T-093)', () => {
  it('are short, non-empty and unique', () => {
    expect(new Set(EARTH_TEXTS).size).toBe(EARTH_TEXTS.length)
    for (const t of EARTH_TEXTS) {
      expect(t.trim().length).toBeGreaterThan(5)
      expect(t.length).toBeLessThanOrEqual(80)
    }
  })

  it('claim nothing beyond the method: no fire counts, burned area, cause, forecast or accuracy', () => {
    const joined = EARTH_TEXTS.join(' ').toLowerCase()
    expect(joined).not.toMatch(/\bfires\b/)
    expect(joined).not.toContain('burned area')
    expect(joined).not.toMatch(/\bcaus(e|ed|es)\b/)
    expect(joined).not.toMatch(/\bpredict|\bforecast|\baccura(cy|te)\b/)
    expect(joined).not.toMatch(/\banomal(y|ies)\b/)
    expect(joined).not.toMatch(/\bunusual\b/)
  })

  it('state no number, so nothing here needs the number inventory', () => {
    for (const t of EARTH_TEXTS) expect(t).not.toMatch(/\d/)
  })

  it('say the low-zoom rule is about drawing, and name the two verdicts kept strong', () => {
    expect(SIGNAL_RULE).toContain('above and below normal')
    expect(SIGNAL_RULE.toLowerCase()).toContain('drawn')
  })
})
