import { createRef } from 'react'
import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EntityMonth, Metadata } from '../../api/contract.ts'
import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { GLOSSARY, HOW_TO_READ } from '../../content/plainLanguage.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { HOWTO_KEY, howToOpenAtStart, isHowToDismissed, rememberHowToDismissed } from '../../state/howto.ts'
import { SummaryCard } from '../summary/SummaryCard.tsx'
import { Header } from './Header.tsx'
import { HowToRead } from './HowToRead.tsx'
import { StoryCaption } from './StoryCaption.tsx'
import { activeStory, selectableStories } from './stories.ts'

// SYNTHETIC test data: records are built from each story's own stored facts to check that the card and the story agree.
// They are fixtures, not NASA observations.
const meta: Metadata = {
  contract_version: '1',
  method_version: '0.0.0-test',
  synthetic: true,
  first_month: '2002-07',
  latest_month: '2026-10',
  provisional_months: [],
  citation: '',
}

function recordFromStory(s: FeaturedStory): EntityMonth {
  const f = s.facts
  return {
    entity_type: s.entityType === 'FIRE_REGION' ? 'COUNTRY' : s.entityType,
    entity_id: s.entityId,
    entity_name: s.entityName,
    year: s.year,
    month: s.month,
    n_cells: 10,
    raw_by_witness: null,
    estimate: f.estimate,
    ci90_low: f.ci90Low,
    ci90_high: f.ci90High,
    sd: 1,
    raw_combined_cell_days: 1,
    witnesses_used: ['AQUA_MODIS'],
    n_witnesses: 1,
    disagreement_scale: 1,
    baseline_median: f.baselineMedian,
    baseline_p25: f.baselineP25,
    baseline_p75: f.baselineP75,
    pct_of_normal: f.pctOfNormal,
    p_above: f.pAbove,
    p_below: f.pBelow,
    p_within: f.pWithin,
    verdict: f.verdict as EntityMonth['verdict'],
    reason_codes: f.reasonCodes as EntityMonth['reason_codes'],
    data_level: f.dataLevel as EntityMonth['data_level'],
    method_version: '0.0.0-test',
  }
}

const plain = (html: string) =>
  html.replace(/<[^>]+>/g, '').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&')

describe('story rule', () => {
  const idn = FEATURED_STORIES.find((s) => s.id === 'indonesia-2015-09')!
  const area = { entity_type: 'COUNTRY', entity_id: 'IDN' }
  it('is on when the area and the month both equal the story', () => {
    expect(activeStory(area, { year: 2015, month: 9 })).toBe(idn)
  })
  it('clears when the month or the area changes, or there is no month', () => {
    expect(activeStory(area, { year: 2015, month: 10 })).toBeNull()
    expect(activeStory({ entity_type: 'COUNTRY', entity_id: 'BRA' }, { year: 2015, month: 9 })).toBeNull()
    expect(activeStory({ entity_type: 'GLOBAL', entity_id: 'GLOBAL' }, { year: 2015, month: 9 })).toBeNull()
    expect(activeStory({ entity_type: 'CUSTOM', entity_id: 'IDN' }, { year: 2015, month: 9 })).toBeNull()
    expect(activeStory(area, null)).toBeNull()
  })
  it('finds the world story on the world', () => {
    const world = FEATURED_STORIES.find((s) => s.entityType === 'GLOBAL')!
    expect(activeStory({ entity_type: 'GLOBAL', entity_id: 'GLOBAL' }, { year: world.year, month: world.month })).toBe(world)
  })
})

describe('story caption', () => {
  it('shows the stored headline, caption, label, source line, query and report link, and the notes', () => {
    for (const s of selectableStories()) {
      const html = renderToString(<StoryCaption story={s} />)
      const text = plain(html)
      expect(text).toContain(s.headline)
      expect(text).toContain(s.caption)
      expect(text).toContain(s.label)
      expect(text).toContain(s.sourceLine)
      expect(text).toContain(s.query)
      for (const n of s.notes) expect(text).toContain(n)
      expect(html).toContain(`href="${s.reportHref}"`)
    }
  })
  it('the Australia story carries the cannot-determine explanation', () => {
    const aus = FEATURED_STORIES.find((s) => s.entityId === 'AUS')!
    const html = renderToString(<StoryCaption story={aus} />)
    expect(plain(html)).toContain('cannot determine')
    expect(aus.facts.pctOfNormal).not.toBeNull()
  })
})

describe('summary card against the story facts', () => {
  it('shows the same verdict, % of normal, estimate and interval as the story stores', () => {
    for (const s of selectableStories()) {
      const html = renderToString(
        <SummaryCard
          area={{ entity_type: s.entityType as 'COUNTRY' | 'CONTINENT' | 'GLOBAL', entity_id: s.entityId, entity_name: s.entityName }}
          month={{ year: s.year, month: s.month }}
          status="ready"
          records={[recordFromStory(s)]}
          meta={meta}
          headingRef={createRef()}
          download={null}
        />,
      )
      expect(html).toContain(VERDICT_PRESENTATION[s.facts.verdict as keyof typeof VERDICT_PRESENTATION].label)
      if (s.facts.pctOfNormal !== null) expect(html).toContain(`>${Math.round(s.facts.pctOfNormal)}<`)
      if (s.facts.estimate !== null) expect(html).toContain(s.facts.estimate.toFixed(1))
      if (s.facts.ci90Low !== null && s.facts.ci90High !== null)
        expect(html).toContain(`${s.facts.ci90Low.toFixed(1)} to ${s.facts.ci90High.toFixed(1)}`)
    }
  })
  it('the story caption quotes the rounded % of normal that the card shows', () => {
    for (const s of selectableStories()) {
      if (s.facts.pctOfNormal !== null) expect(s.caption.startsWith(`${Math.round(s.facts.pctOfNormal)}% of`)).toBe(true)
    }
  })
})

describe('How to read this', () => {
  it('shows the approved steps, the five verdicts and the glossary, with a close button', () => {
    const html = renderToString(<HowToRead onClose={() => {}} />)
    for (const step of HOW_TO_READ) expect(plain(html)).toContain(step.title)
    for (const g of GLOSSARY) expect(plain(html)).toContain(g.term)
    for (const v of Object.values(VERDICT_PRESENTATION)) expect(html).toContain(v.label)
    expect(html).toContain(UI.HOW_TO_READ_CLOSE)
    expect(html).toContain('id="how-to-read"')
  })
  it('the header link says whether the panel is open', () => {
    expect(renderToString(<Header showMethods onOpenMethods={() => {}} howToOpen />)).toContain('aria-expanded="true"')
    expect(renderToString(<Header showMethods onOpenMethods={() => {}} />)).toContain('aria-expanded="false"')
  })
})

describe('dismissal storage', () => {
  afterEach(() => vi.unstubAllGlobals())
  const stubStorage = (store: Record<string, string>) =>
    vi.stubGlobal('window', {
      localStorage: {
        getItem: (k: string) => store[k] ?? null,
        setItem: (k: string, v: string) => {
          store[k] = v
        },
      },
    })
  it('uses the key gfh.howto.dismissed and remembers the dismissal', () => {
    const store: Record<string, string> = {}
    stubStorage(store)
    expect(HOWTO_KEY).toBe('gfh.howto.dismissed')
    expect(isHowToDismissed()).toBe(false)
    expect(howToOpenAtStart('')).toBe(true)
    rememberHowToDismissed()
    expect(store[HOWTO_KEY]).toBe('1')
    expect(isHowToDismissed()).toBe(true)
    expect(howToOpenAtStart('')).toBe(false)
  })
  it('opens only on a first visit without link parameters', () => {
    stubStorage({})
    expect(howToOpenAtStart('?area=IDN')).toBe(false)
    expect(howToOpenAtStart('?tab=evidence')).toBe(false)
  })
  it('works when storage is blocked: nothing throws and the panel counts as not dismissed', () => {
    const blocked = {
      get localStorage(): never {
        throw new Error('blocked')
      },
    }
    vi.stubGlobal('window', blocked)
    expect(isHowToDismissed()).toBe(false)
    expect(() => rememberHowToDismissed()).not.toThrow()
    expect(howToOpenAtStart('')).toBe(true)
  })
})
