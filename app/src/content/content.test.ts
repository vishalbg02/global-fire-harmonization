import { describe, expect, it } from 'vitest'
import { REASON_CODES, VERDICTS } from '../api/contract.ts'
import { REASON_CODE_SHORT } from './reasonCodes.ts'
import { REASON_TEXTS } from './reasonTexts.ts'
import { WITNESS_NAMES } from './witnesses.ts'
import { WITNESSES } from '../api/contract.ts'
import { VERDICT_PRESENTATION } from './verdicts.ts'

describe('verdict presentation', () => {
  it('has a label, icon, colour and description for every verdict', () => {
    for (const v of VERDICTS) {
      const p = VERDICT_PRESENTATION[v]
      expect(p.label.length).toBeGreaterThan(0)
      expect(p.icon.length).toBeGreaterThan(0)
      expect(p.color).toHaveLength(3)
      expect(p.description.length).toBeGreaterThan(0)
    }
  })

  it('never describes NO_DETECTED_ACTIVITY as below normal', () => {
    const p = VERDICT_PRESENTATION.NO_DETECTED_ACTIVITY
    expect(`${p.label} ${p.description}`.toLowerCase()).not.toContain('below')
  })

  it('uses a different icon for every verdict, so colour is never the only cue', () => {
    expect(new Set(VERDICTS.map((v) => VERDICT_PRESENTATION[v].icon)).size).toBe(VERDICTS.length)
  })
})

describe('reason code short labels', () => {
  it('has a label for every reason code', () => {
    for (const code of REASON_CODES) expect(REASON_CODE_SHORT[code].length).toBeGreaterThan(0)
  })
})


describe('plain-language reason texts (T-036 acceptance)', () => {
  it('has text for every contract reason code: this fails if a code is added without text', () => {
    for (const code of REASON_CODES) {
      expect(typeof REASON_TEXTS[code]).toBe('string')
      expect(REASON_TEXTS[code].trim().length).toBeGreaterThan(0)
    }
    expect(Object.keys(REASON_TEXTS).sort()).toEqual([...REASON_CODES].sort())
  })

  it('uses the Lead-approved wording of the nine drafts', () => {
    expect(REASON_TEXTS.OUTAGE).toBe("Satellite data were missing for part of this month, so it can't be judged reliably.")
    expect(REASON_TEXTS.INSUFFICIENT_BASELINE).toBe('There is too little historical fire activity here to define what is normal.')
    expect(REASON_TEXTS.INSUFFICIENT_OVERLAP).toBe("There weren't enough months when the satellites overlapped here to calibrate them reliably.")
    expect(REASON_TEXTS.WITNESS_DISAGREEMENT).toBe('The satellites disagree more than expected, so the uncertainty was widened.')
    expect(REASON_TEXTS.WIDE_INTERVAL).toBe('The uncertainty range is too wide for a confident verdict.')
    expect(REASON_TEXTS.PROVISIONAL_NRT).toBe('Based on near-real-time data; values may change when science-quality data arrive.')
    expect(REASON_TEXTS.AQUA_DRIFT_ERA).toBe("Aqua MODIS's orbit has drifted, so it is not used as a witness for this period.")
    expect(REASON_TEXTS.SINGLE_WITNESS).toBe('Only one satellite contributed this month.')
    expect(REASON_TEXTS.POOLED_CALIBRATION).toBe('Local data were sparse, so calibration borrows from the wider region.')
  })

  it('uses the Lead replacement text for DIURNAL_CAVEAT, without the unsourced claim', () => {
    expect(REASON_TEXTS.DIURNAL_CAVEAT).toBe(
      'Satellites pass over at fixed times of day. Fires that burn mainly at other hours can be under-counted, and differently by each satellite.',
    )
    expect(REASON_TEXTS.DIURNAL_CAVEAT).not.toContain('reported')
  })

  it('never says "number of fires"', () => {
    for (const code of REASON_CODES) expect(REASON_TEXTS[code].toLowerCase()).not.toContain('number of fires')
  })
})

describe('witness names', () => {
  it('has a display name for every witness', () => {
    for (const w of WITNESSES) expect(WITNESS_NAMES[w].length).toBeGreaterThan(0)
    expect(WITNESS_NAMES.TERRA_MODIS).toContain('raw only')
    expect(WITNESS_NAMES.NOAA21_VIIRS).toContain('reserved')
  })
})
