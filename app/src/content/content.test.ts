import { describe, expect, it } from 'vitest'
import { REASON_CODES, VERDICTS } from '../api/contract.ts'
import { REASON_CODE_SHORT } from './reasonCodes.ts'
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
