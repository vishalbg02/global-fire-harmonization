import { describe, expect, it } from 'vitest'
import * as T from './timeline.ts'

const SENTENCES = [
  T.SLIDER_LABEL,
  T.PREVIOUS_MONTH,
  T.NEXT_MONTH,
  T.NO_MONTH,
  T.PROVISIONAL,
  T.PROVISIONAL_KEY_LABEL,
  T.NO_MAP_SUFFIX,
  T.SATELLITE_JOINS_LABEL,
  T.LINE_HARMONIZED,
  T.LINE_RAW,
  T.LINE_LOADING,
  T.sliderValueText({ year: 2015, month: 9 }, { provisional: true, noMap: true }),
  T.joinsSummary([{ label: 'S-NPP VIIRS', month: { year: 2012, month: 1 } }]),
]

describe('timeline texts (T-093)', () => {
  it('are non-empty and plain', () => {
    for (const s of SENTENCES) {
      expect(s.trim().length).toBeGreaterThan(3)
      expect(s).not.toContain('!')
    }
  })

  it('claim nothing beyond the method: no fire counts, burned area, cause, forecast or accuracy', () => {
    const joined = SENTENCES.join(' ').toLowerCase()
    expect(joined).not.toMatch(/\bfires\b/)
    expect(joined).not.toMatch(/burned area|area burned/)
    expect(joined).not.toMatch(/\bcaused?\b/)
    expect(joined).not.toMatch(/\bpredict|\bforecast|\baccura/)
    expect(joined).not.toMatch(/\banomal(y|ies)\b/)
  })

  it('say what the line shows and that missing values are gaps, never zero', () => {
    expect(T.LINE_HARMONIZED).toContain('harmonized estimate')
    expect(T.LINE_RAW).toContain('raw fire-active cell-days')
    expect(T.LINE_RAW).toContain('not converted')
    for (const s of [T.LINE_HARMONIZED, T.LINE_RAW]) expect(s).toContain('Gaps are months without')
  })

  it('read the month out with its state', () => {
    expect(T.sliderValueText({ year: 2015, month: 9 }, { provisional: false, noMap: false })).toBe('September 2015')
    expect(T.sliderValueText({ year: 2026, month: 10 }, { provisional: true, noMap: false })).toBe('October 2026, provisional')
    expect(T.sliderValueText({ year: 2010, month: 3 }, { provisional: false, noMap: true })).toBe('March 2010, no offline map')
    expect(T.sliderValueText(null, { provisional: false, noMap: false })).toBe(T.NO_MONTH)
    expect(T.joinsSummary([])).toBe('')
    expect(T.joinsSummary([{ label: 'S-NPP VIIRS', month: { year: 2012, month: 1 } }])).toBe('Satellite joins: S-NPP VIIRS in January 2012.')
  })
})
