import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import * as T from '../../content/monthPicker.ts'
import { monthRange } from '../../state/months.ts'
import { MonthPicker } from './MonthPicker.tsx'
import { MonthSelector } from './MonthSelector.tsx'

// SYNTHETIC list with the shape of the record; the real one comes from the metadata.
const months = monthRange('2002-07', '2026-11', ['2026-08', '2026-09', '2026-10', '2026-11'])
const noop = () => {}

describe('MonthPicker render (T-087)', () => {
  const html = renderToString(<MonthPicker months={months} value={{ year: 2019, month: 12 }} onChoose={noop} onClose={noop} />)

  it('has a year select, a typing field and a button for every month of every year, each with its name', () => {
    expect(html).toContain(`aria-label="${T.PICKER_YEAR_LABEL}"`)
    expect(html).toContain(T.PICKER_TYPE_LABEL)
    expect((html.match(/<option /g) ?? []).length).toBe(25)
    expect((html.match(/class="btn month-picker-month/g) ?? []).length).toBe(25 * 12)
    expect(html).toContain('aria-label="December 2019"')
    expect(html).toContain('aria-label="July 2002"')
  })

  it('marks the chosen month, disables months outside the record and marks provisional months', () => {
    expect(html).toMatch(/aria-pressed="true"[^>]*aria-label="December 2019"|aria-label="December 2019"[^>]*aria-pressed="true"/)
    expect((html.match(/disabled=""/g) ?? []).length).toBe(25 * 12 - months.length) // 6 months of 2002 before July and 1 after November 2026
    expect(html).toContain('aria-label="June 2002"')
    expect(html).toMatch(/is-provisional[^>]*aria-label="October 2026, provisional"/)
    expect(html).not.toContain('aria-label="July 2026, provisional"')
    expect((html.match(/, provisional"/g) ?? []).length).toBe(4)
  })

  it('names itself and explains the dot', () => {
    expect(html).toContain('role="dialog"')
    expect(html).toContain(T.PICKER_LEGEND)
  })
})

describe('MonthSelector with the picker (T-087)', () => {
  const html = renderToString(<MonthSelector months={months} value={{ year: 2019, month: 12 }} onChange={noop} />)

  it('keeps the existing controls and adds year steps, year ticks and the picker button', () => {
    expect(html).toContain('aria-label="Previous month"')
    expect(html).toContain('aria-label="Next month"')
    expect(html).toContain('aria-label="Month slider"')
    expect(html).toContain(`aria-label="${T.PREVIOUS_YEAR_LABEL}"`)
    expect(html).toContain(`aria-label="${T.NEXT_YEAR_LABEL}"`)
    expect(html).toContain('December 2019')
    expect(html).toContain('aria-haspopup="dialog"')
    expect(html).toContain('aria-expanded="false"')
    for (const year of [2005, 2010, 2015, 2020, 2025]) expect(html).toContain(`>${year}<`)
  })

  it('has the picker closed to start with, and describes the keys for the slider', () => {
    expect(html).not.toContain('role="dialog"')
    expect(html).toContain(T.SLIDER_HINT)
  })

  it('disables the year steps at the ends of the record and with no month', () => {
    const atEnd = renderToString(<MonthSelector months={months} value={{ year: 2026, month: 11 }} onChange={noop} />)
    expect(atEnd).toMatch(/<button[^>]*disabled=""[^>]*aria-label="Next year"/)
    const none = renderToString(<MonthSelector months={[]} value={null} onChange={noop} />)
    expect(none).toContain('No month available')
    expect(none).toMatch(/<button[^>]*disabled=""[^>]*aria-label="Previous year"/)
  })
})

describe('texts (T-087)', () => {
  it('are plain and state the valid range from the arguments', () => {
    expect(T.invalidMonthMessage('2002-07', '2026-11')).toBe('Use YYYY-MM, from 2002-07 to 2026-11.')
    for (const text of [T.PICKER_LEGEND, T.SLIDER_HINT]) expect(text).not.toContain('!')
  })
})
