import { describe, expect, it } from 'vitest'
import * as A from './answer.ts'
import { SATELLITE_TIMELINE } from './witnessTimeline.ts'

// Every user-facing sentence of answer.ts, the templates filled with placeholder words (no number is invented here).
const SENTENCES: string[] = [
  A.PCT_UNIT,
  A.PROVISIONAL_MARK,
  A.BAR_ESTIMATE,
  A.BAR_INTERVAL,
  A.BAR_NORMAL,
  A.BAR_MEDIAN,
  A.BAR_RANGE('low', 'high'),
  A.BAR_INTERVAL_MISSING,
  A.BAR_NOT_AVAILABLE,
  A.BAR_UNIT_LABEL,
  A.BAR_NAME('Testland'),
  A.BAR_TEXT({ estimate: 'e', interval: 'i', normal: 'n', median: 'm', unit: 'u' }),
  A.BAR_NONE,
  A.SPARK_CAPTION_SHORT('first', 'last', 'selected'),
  A.WHY_HEADING,
  A.WHY_LABEL,
  A.STORY_CARD_TITLE,
  A.TOAST_CSV_DOWNLOADED,
  A.CSV_BUTTON,
  A.CSV_BUTTON_NAME('Testland'),
  A.CSV_PREPARING,
  A.CSV_ABOUT,
  A.CSV_FIRMS_LINK,
  A.ACTIONS_LABEL,
  A.SUMMARY_LOADING,
  A.ANALYTICS_LOADING,
  A.SUMMARY_ERROR,
  A.RAW_HARMONIZED_TAKEAWAY,
]

describe('answer panel texts (T-093)', () => {
  it('are all non-empty', () => {
    for (const text of SENTENCES) expect(text.trim().length).toBeGreaterThan(0)
  })

  it('claim nothing beyond the method: no fire counts, burned area, cause, forecast or accuracy', () => {
    for (const text of SENTENCES) {
      const lower = text.toLowerCase()
      expect(lower).not.toMatch(/\bfires\b/)
      expect(lower).not.toMatch(/burned area|area burned|burnt/)
      expect(lower).not.toMatch(/\bcaus(e|ed|es|ing)\b/)
      expect(lower).not.toMatch(/\bpredict|\bforecast|\baccura(te|cy)\b/)
      expect(lower).not.toMatch(/\banomal(y|ies)\b|\bunusual\b/)
    }
  })

  it('type no number: only the templates receive values', () => {
    const fixed = SENTENCES.filter((t) => t !== A.RAW_HARMONIZED_TAKEAWAY)
    for (const text of fixed) expect(text.replace(/90%|NOAA-20|S-NPP/g, '')).not.toMatch(/\d/)
    expect(A.TOAST_MS).toBe(3000)
  })

  it('keep the accessible name of the CSV button starting with its visible words (WCAG 2.5.3)', () => {
    expect(A.CSV_BUTTON_NAME('Indonesia').startsWith(A.CSV_BUTTON)).toBe(true)
    expect(A.CSV_BUTTON_NAME('Indonesia')).toBe('Download CSV: Indonesia')
  })
})

describe('the takeaway under the raw-against-harmonized chart', () => {
  const joined = (witness: string) => SATELLITE_TIMELINE.find((e) => e.witness === witness)!.start

  it('takes the two satellite dates from witnessTimeline.ts', () => {
    expect(joined('SNPP_VIIRS').startsWith('2012-01')).toBe(true)
    expect(joined('NOAA20_VIIRS').startsWith('2018-04')).toBe(true)
    expect(A.RAW_HARMONIZED_TAKEAWAY).toContain('S-NPP VIIRS from January 2012')
    expect(A.RAW_HARMONIZED_TAKEAWAY).toContain('NOAA-20 VIIRS from April 2018')
  })

  it('describes the method (raw sums every satellite; harmonized stays on the Aqua MODIS scale) and prints no other number', () => {
    expect(A.RAW_HARMONIZED_TAKEAWAY).toContain('Raw adds up the detections of every satellite')
    expect(A.RAW_HARMONIZED_TAKEAWAY).toContain('the harmonized estimate keeps every month on the Aqua MODIS scale')
    const withoutDatesAndNames = A.RAW_HARMONIZED_TAKEAWAY.replace(/January 2012|April 2018|NOAA-20|S-NPP/g, '')
    expect(withoutDatesAndNames).not.toMatch(/\d/)
    // No size of a jump is claimed.
    expect(A.RAW_HARMONIZED_TAKEAWAY.toLowerCase()).not.toMatch(/times|double|triple|percent|%/)
  })
})
