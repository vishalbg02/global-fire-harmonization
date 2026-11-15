import { describe, expect, it } from 'vitest'
import { GLOSSARY, HOW_TO_READ, IN_PLAIN_WORDS } from './plainLanguage.ts'
import { disagreementNote } from './evidenceText.ts'

const ALL = [
  ...HOW_TO_READ.flatMap((s) => [s.title, s.text]),
  ...GLOSSARY.flatMap((g) => [g.term, g.hint]),
  ...IN_PLAIN_WORDS,
]

describe('plain-language texts (T-076)', () => {
  it('has non-empty, unique ids and texts', () => {
    for (const list of [HOW_TO_READ, GLOSSARY]) {
      expect(new Set(list.map((x) => x.id)).size).toBe(list.length)
    }
    for (const text of ALL) expect(text.trim().length).toBeGreaterThan(5)
    expect(HOW_TO_READ.length).toBeGreaterThanOrEqual(5)
    expect(HOW_TO_READ.length).toBeLessThanOrEqual(6)
  })

  it('defines the terms a first-time reader meets', () => {
    const terms = GLOSSARY.map((g) => g.term.toLowerCase()).join(' | ')
    for (const t of ['cell-day', 'aqua-equivalent', 'harmonized', 'normal range', '% of normal', '90% interval', 'verdict', 'cannot determine', 'provisional', 'raw']) {
      expect(terms).toContain(t)
    }
  })

  it('claims nothing beyond the method: no fire counts, burned area, cause or forecast', () => {
    const joined = ALL.join(' ').toLowerCase()
    expect(joined).not.toContain('number of fires, ')
    expect(joined).not.toMatch(/\banomal(y|ies)\b/)
    expect(joined).not.toMatch(/\b(caused by|because of the weather|will burn|forecast|predict)/)
    // "burned area" and "number of fires" appear only in a negation
    for (const text of ALL) {
      const lower = text.toLowerCase()
      for (const phrase of ['burned area', 'area burned', 'number of fires', 'count fires']) {
        if (lower.includes(phrase)) expect(lower).toMatch(/\bnot\b|\bno\b|\bdoes not\b|\bnever\b/)
      }
    }
  })

  it('states the approved baseline and threshold exactly (D-028)', () => {
    const joined = ALL.join(' ')
    expect(joined).toContain('2003 to 2022')
    expect(joined).toContain('80%')
    expect(joined).toContain('25th to the 75th percentile')
  })

  it('uses no unexplained method jargon', () => {
    const joined = ALL.join(' ').toLowerCase()
    for (const word of ['witness', 'stratum', 'strata', 'kappa', 'overdispersion', 'pooling']) expect(joined).not.toContain(word)
  })
})

describe('disagreement note (T-076)', () => {
  it('is a routine adjustment up to a scale of 2 and a listed caveat above it', () => {
    expect(disagreementNote(1.78)).toContain('routine adjustment, not a caveat')
    expect(disagreementNote(2)).toContain('routine adjustment, not a caveat')
    expect(disagreementNote(2.5)).toContain('listed as a caveat')
    expect(disagreementNote(2.5)).not.toContain('routine')
  })
})
