import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { MethodsPage } from '../components/methods/MethodsPage.tsx'
import { FEATURED_STORIES } from './featured.ts'
import * as HELP from './help.ts'
import {
  EXPLAINERS,
  SHORTCUT_ROWS,
  TOUR_STEPS,
  globeHint,
  possessive,
  startHereWorld,
  storyQuestion,
  tourCount,
} from './help.ts'
import type { ExplainerId, ShortcutId } from './help.ts'
import { GLOSSARY } from './plainLanguage.ts'

// Every help text of T-093. SYNTHETIC: no data are involved; the stories are the generated featured.ts.

const IDS: ExplainerId[] = [
  'pct-of-normal',
  'interval-90',
  'probability',
  'cell-days',
  'cannot-determine',
  'no-detected-activity',
  'provisional',
  'raw-vs-harmonized',
  'satellite-view',
  'normal-range',
]

/** Every user-facing string of help.ts: constants, the tables, and the functions with sample arguments. */
const ALL_TEXTS: string[] = [
  ...(Object.values(HELP) as unknown[]).filter((v): v is string => typeof v === 'string'),
  ...Object.values(EXPLAINERS).flatMap((e) => [e.term, e.text]),
  ...TOUR_STEPS.flatMap((s) => [s.title, s.text]),
  ...SHORTCUT_ROWS.flatMap((r) => [...r.keys, r.label]),
  ...FEATURED_STORIES.map(storyQuestion),
  globeHint(true),
  globeHint(false),
  startHereWorld('October 2026'),
  tourCount(0, 5),
]

const methodsHtml = () =>
  renderToString(
    createElement(QueryClientProvider, { client: new QueryClient() }, createElement(MethodsPage, { onBack: () => {} })),
  )

describe('"?" explainers', () => {
  it('has a term, one or two sentences and an anchor for every id', () => {
    expect(Object.keys(EXPLAINERS).sort()).toEqual([...IDS].sort())
    for (const id of IDS) {
      const e = EXPLAINERS[id]
      expect(e.term.trim().length).toBeGreaterThan(2)
      expect(e.text.trim().length).toBeGreaterThan(20)
      const sentences = e.text.split(/(?<=\.)\s+(?=[A-Z"])/).length
      expect(sentences, id).toBeLessThanOrEqual(3)
      expect(e.anchor).toMatch(/^[a-z0-9-]+$/)
    }
  })

  it('links every "Learn more" to an anchor that exists on the methods page', () => {
    const html = methodsHtml()
    for (const id of IDS) expect(html, `${id} -> #${EXPLAINERS[id].anchor}`).toContain(`id="${EXPLAINERS[id].anchor}"`)
  })

  it('reuses the approved glossary word for word wherever it has the term', () => {
    const hint = (id: string) => GLOSSARY.find((g) => g.id === id)?.hint ?? ''
    expect(EXPLAINERS['pct-of-normal'].text).toBe(hint('pct-of-normal'))
    expect(EXPLAINERS['interval-90'].text).toBe(hint('interval-90'))
    expect(EXPLAINERS['cannot-determine'].text).toBe(hint('cannot-determine'))
    expect(EXPLAINERS.provisional.text).toBe(hint('provisional'))
    expect(EXPLAINERS['normal-range'].text).toBe(hint('normal-range'))
    expect(EXPLAINERS['cell-days'].text).toBe(`${hint('cell-day')} ${hint('aqua-equivalent')}`)
    expect(EXPLAINERS['raw-vs-harmonized'].text).toBe(`${hint('raw')} ${hint('harmonized')}`)
  })

  it('states the approved 80% threshold and calls imagery context, not data', () => {
    expect(EXPLAINERS.probability.text).toContain('80%')
    expect(EXPLAINERS['satellite-view'].text).toContain('context, not data')
    expect(EXPLAINERS['satellite-view'].text).toContain('does not change a verdict')
  })
})

describe('the guided tour texts', () => {
  it('has five steps in the agreed order, each one sentence or two', () => {
    expect(TOUR_STEPS.map((s) => s.id)).toEqual(['place', 'month', 'verdict', 'why', 'raw'])
    expect(TOUR_STEPS.map((s) => s.title)).toEqual(['Pick a place', 'Pick a month', 'Read the verdict', 'Why this verdict', 'Raw vs harmonized'])
    for (const s of TOUR_STEPS) expect(s.text.split(/\.\s/).length).toBeLessThanOrEqual(2)
  })

  it('points "Why this verdict" back at the answer panel when the reasons are not on screen', () => {
    expect(TOUR_STEPS.find((s) => s.id === 'why')?.fallback).toBe('verdict')
  })

  it('says honestly that the panel shows example questions before anything is chosen', () => {
    expect(TOUR_STEPS.find((s) => s.id === 'verdict')?.text).toContain('Until you choose, it offers three example questions')
  })

  it('counts the steps as "1 of 5"', () => {
    expect(tourCount(0, 5)).toBe('1 of 5')
    expect(tourCount(4, 5)).toBe('5 of 5')
  })
})

describe('Start here questions', () => {
  it('builds each question from the story fields, never by hand', () => {
    const idn = FEATURED_STORIES.find((s) => s.id === 'indonesia-2015-09')
    expect(idn).toBeDefined()
    if (idn !== undefined) expect(storyQuestion(idn)).toBe("Was Indonesia's fire activity in September 2015 unusual?")
    for (const s of FEATURED_STORIES) {
      const q = storyQuestion(s)
      expect(q).toContain(s.entityName)
      expect(q).toContain(String(s.year))
      expect(q.endsWith('?')).toBe(true)
    }
  })

  it('writes the possessive of names ending in s without an extra s', () => {
    expect(possessive('Indonesia')).toBe("Indonesia's")
    expect(possessive('Philippines')).toBe("Philippines'")
  })

  it('names the month the world would be shown for, when it is known', () => {
    expect(startHereWorld(null)).toBe('Show the whole world')
    expect(startHereWorld('October 2026')).toBe('Show the whole world for October 2026')
  })
})

describe('keyboard shortcut rows', () => {
  it('lists every shortcut once', () => {
    const ids: ShortcutId[] = ['month-prev', 'month-next', 'year-prev', 'year-next', 'play', 'globe', 'satellite', 'search', 'shortcuts', 'close']
    const listed = SHORTCUT_ROWS.flatMap((r) => r.ids)
    expect([...listed].sort()).toEqual([...ids].sort())
    for (const r of SHORTCUT_ROWS) expect(r.keys.length).toBeGreaterThan(0)
  })
})

describe('the globe hint', () => {
  it('names the zoom key of the platform', () => {
    expect(globeHint(true)).toBe('Drag to turn the Earth; ⌘ + scroll to zoom')
    expect(globeHint(false)).toBe('Drag to turn the Earth; Ctrl + scroll to zoom')
  })
})

describe('every help text claims nothing beyond the method', () => {
  it('has no fire count, burned area, cause, forecast, prediction or accuracy claim', () => {
    for (const text of ALL_TEXTS) {
      const lower = text.toLowerCase()
      // "fires" and "burned" appear only in a negation (the approved glossary: "not how many fires there were or how much burned").
      if (/\bfires\b/.test(lower)) expect(lower, text).toMatch(/not how many fires/)
      expect(lower, text).not.toMatch(/\bcaused?\b|\bbecause of\b/)
      expect(lower, text).not.toMatch(/\bpredict|\bforecast|\baccura(te|cy)\b/)
      expect(lower, text).not.toMatch(/\banomal(y|ies)\b/)
      if (lower.includes('burn')) expect(lower, text).toMatch(/\bnot\b/)
      expect(lower, text).not.toContain('burned area')
    }
  })

  it('uses no marketing words and no emoji', () => {
    for (const text of ALL_TEXTS) {
      expect(text.toLowerCase()).not.toMatch(/\b(unlock|powerful|seamless|insights?|discover|amazing|easily)\b/)
      expect(text).not.toMatch(/\p{Extended_Pictographic}/u)
    }
  })
})
