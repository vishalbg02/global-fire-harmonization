import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { EntityItem, EntityMonth, Metadata } from '../../api/contract.ts'
import { RawOnlyContext } from '../../content/rawOnly.ts'
import * as UI from '../../content/ui.ts'
import { FEATURED_STORIES } from '../../content/featured.ts'
import { TAB_IDS, setTabParam, tabFromSearch } from '../../state/tabs.ts'
import { WORLD } from '../../state/selection.ts'
import { MAX_SEARCH_RESULTS, parseAreaOption, searchAreas } from '../area/areaSearch.ts'
import { AreaSearch } from '../area/AreaSearch.tsx'
import { MapModeSwitch, selectMode } from '../map/MapModeSwitch.tsx'
import { MapSourceLine } from '../map/MapSourceLine.tsx'
import { DATASET_DOIS } from '../../content/methods.ts'
import { firmsProducts, productCode } from '../map/mapSource.ts'
import { PLAY_INTERVAL_MS, nextPlayIndex, playStartIndex } from '../map/playback.ts'
import { MonthSelector } from '../map/MonthSelector.tsx'
import { Sparkline } from '../summary/Sparkline.tsx'
import { NO_CAVEATS_TEXT } from '../../content/evidenceText.ts'
import { SummaryCard, sentence } from '../summary/SummaryCard.tsx'
import { buildSpark, countGaps, sparkWindow } from '../summary/sparkline.ts'
import type { SparkPoint } from '../summary/sparkline.ts'
import { Header } from './Header.tsx'
import { StoryChips, selectableStories, storyLabel } from './StoryChips.tsx'
import { copyText } from './copyLink.ts'
import { TopAnomalies } from '../anomalies/TopAnomalies.tsx'
import { CaptionLine } from '../common/CaptionLine.tsx'
import { createRef } from 'react'

// SYNTHETIC test data. Not NASA observations.
const COUNTRIES: EntityItem[] = [
  { entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil', bbox: [-56, -12, -53, -9.5] },
  { entity_type: 'COUNTRY', entity_id: 'BRN', entity_name: 'Brunei', bbox: [114, 4, 115, 5] },
  { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia', bbox: [95, -11, 141, 6] },
]
const CONTINENTS: EntityItem[] = [{ entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'Asia', bbox: [60, -10, 150, 55] }]

describe('tab in the link', () => {
  it('reads each valid tab and ignores an invalid or missing one', () => {
    for (const t of TAB_IDS) expect(tabFromSearch(`?tab=${t}`)).toBe(t)
    expect(tabFromSearch('?tab=nope')).toBe('calendar')
    expect(tabFromSearch('')).toBe('calendar')
    expect(TAB_IDS).toEqual(['calendar', 'satellites', 'evidence', 'anomalies'])
  })
  it('writes the tab, leaving the default out', () => {
    const p = new URLSearchParams('area=GLOBAL')
    setTabParam(p, 'evidence')
    expect(p.get('tab')).toBe('evidence')
    setTabParam(p, 'calendar')
    expect(p.has('tab')).toBe(false)
  })
})

describe('area search', () => {
  it('finds countries and continents, names that start with the text first', () => {
    const labels = searchAreas(COUNTRIES, CONTINENTS, 'br').map((o) => o.label)
    expect(labels).toEqual(['Brazil', 'Brunei'])
    expect(searchAreas(COUNTRIES, CONTINENTS, 'ia').map((o) => o.label)).toEqual(['Asia', 'Indonesia'])
  })
  it('matches a code exactly and is case-insensitive', () => {
    expect(searchAreas(COUNTRIES, CONTINENTS, 'idn')[0]?.label).toBe('Indonesia')
    expect(searchAreas(COUNTRIES, CONTINENTS, 'ASIA')[0]?.id).toBe('CONTINENT:AS')
  })
  it('has the world, offers a short list for empty text, and says nothing for no match', () => {
    expect(searchAreas(COUNTRIES, CONTINENTS, 'wor')[0]?.id).toBe('GLOBAL:GLOBAL')
    expect(searchAreas(COUNTRIES, CONTINENTS, '').length).toBeLessThanOrEqual(MAX_SEARCH_RESULTS)
    expect(searchAreas(COUNTRIES, CONTINENTS, 'zzz')).toEqual([])
    expect(searchAreas(undefined, undefined, 'br')).toEqual([])
    expect(parseAreaOption('COUNTRY:BRA')).toEqual({ type: 'COUNTRY', entityId: 'BRA' })
  })
  it('renders a labelled combobox showing the selected area', () => {
    const html = renderToString(
      <AreaSearch
        area={{ entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil' }}
        countries={COUNTRIES}
        continents={CONTINENTS}
        listsFailed={false}
        onChooseEntity={() => {}}
        onChooseWorld={() => {}}
      />,
    )
    expect(html).toContain('role="combobox"')
    expect(html).toContain('value="Brazil"')
    expect(html).toContain(UI.SEARCH_LABEL)
  })
  it('says so when the lists failed', () => {
    const html = renderToString(
      <AreaSearch area={WORLD} countries={undefined} continents={undefined} listsFailed onChooseEntity={() => {}} onChooseWorld={() => {}} />,
    )
    expect(html).toContain('role="alert"')
  })
})

describe('time-lapse', () => {
  it('advances one month per step and stops at the last', () => {
    expect(PLAY_INTERVAL_MS).toBe(1200)
    expect(nextPlayIndex(0, 3)).toBe(1)
    expect(nextPlayIndex(1, 3)).toBe(2)
    expect(nextPlayIndex(2, 3)).toBeNull()
    expect(nextPlayIndex(-1, 3)).toBeNull()
  })
  it('starts from the first month when at the end or unknown', () => {
    expect(playStartIndex(2, 3)).toBe(0)
    expect(playStartIndex(-1, 3)).toBe(0)
    expect(playStartIndex(1, 3)).toBe(1)
  })
  it('the month control has Play, labelled, with the previous and next buttons and the slider', () => {
    const months = [
      { year: 2026, month: 9, provisional: false },
      { year: 2026, month: 10, provisional: false },
    ]
    const html = renderToString(<MonthSelector months={months} value={{ year: 2026, month: 9 }} onChange={() => {}} />)
    expect(html).toContain(`aria-label="${UI.PLAY_LABEL}"`)
    expect(html).toContain('aria-pressed="false"')
    expect(html).toContain('aria-label="Month slider"')
  })
})

describe('copy link', () => {
  it('uses the clipboard when it works', async () => {
    let got = ''
    expect(await copyText('https://x', { clipboard: { writeText: async (t) => void (got = t) } })).toBe(true)
    expect(got).toBe('https://x')
  })
  it('falls back to the old route when the clipboard refuses, and reports a failure when both fail', async () => {
    const refuse = { writeText: async () => Promise.reject(new Error('no')) }
    expect(await copyText('a', { clipboard: refuse, legacy: () => true })).toBe(true)
    expect(await copyText('a', { clipboard: refuse, legacy: () => false })).toBe(false)
    expect(await copyText('a', { clipboard: undefined, legacy: () => false })).toBe(false)
    expect(await copyText('a', { clipboard: undefined, legacy: () => { throw new Error('x') } })).toBe(false)
  })
})

describe('map mode switch', () => {
  it('follows the drawing flags', () => {
    expect(selectMode(false, false)).toBe('country')
    expect(selectMode(true, false)).toBe('rectangle')
    expect(selectMode(false, true)).toBe('polygon')
  })
  it('offers Country, Rectangle and Polygon as a radio group with a hint', () => {
    const html = renderToString(<MapModeSwitch mode="rectangle" onChange={() => {}} />)
    for (const label of ['Country', 'Rectangle', 'Polygon']) expect(html).toContain(`>${label}<`)
    expect(html).toMatch(/<input[^>]*checked=""[^>]*value="rectangle"/)
    expect(html).toContain(UI.MAP_MODE_HINT.rectangle)
  })
  it('keeps Country available and marks the drawing modes unavailable when drawing is off (offline copy)', () => {
    const html = renderToString(<MapModeSwitch mode="country" onChange={() => {}} drawDisabled />)
    expect(html.match(/aria-disabled="true"/g)?.length).toBe(2)
  })
})

describe('source lines', () => {
  it('names the products from the methods page list, the grid and the method version from the metadata, with links', () => {
    expect(productCode('MODIS/Aqua MYD14 V061')).toBe('MYD14')
    expect(productCode('VIIRS S-NPP VNP14IMGT NRT')).toBe('VNP14IMGT')
    expect(productCode('VIIRS/JPSS1 VJ114IMG V002')).toBe('VJ114IMG')
    expect(productCode('MODIS MCD14DL NRT')).toBe('MCD14DL')
    const products = firmsProducts(DATASET_DOIS)
    const { standard, nearRealTime } = products
    expect(standard).toHaveLength(4)
    expect(nearRealTime).toHaveLength(3)
    const html = renderToString(<MapSourceLine methodVersion="9.9.9" products={products} />)
    expect(html).toContain('NASA FIRMS')
    expect(html).toContain('MYD14')
    expect(html).toContain('0.5° grid')
    expect(html).toContain('method 9.9.9')
    expect(html).toContain('href="https://earthdata.nasa.gov/firms"')
    expect(html).toContain('page=methods')
  })
  it('says the method version is not loaded instead of inventing one', () => {
    expect(renderToString(<MapSourceLine methodVersion={null} products={null} />)).toContain(UI.MAP_SOURCE_METHOD_UNKNOWN)
  })
  it('captions carry the unit and the source', () => {
    const html = renderToString(<CaptionLine unit="fire-active cell-days" methodVersion="1.2.3" />)
    expect(html).toContain('Unit: fire-active cell-days.')
    expect(html).toContain('method 1.2.3')
    expect(renderToString(<CaptionLine unit="u" methodVersion={null} />)).not.toContain('method')
  })
})

const meta: Metadata = {
  contract_version: '1',
  method_version: '0.0.0-test',
  synthetic: true,
  first_month: '2020-01',
  latest_month: '2020-12',
  provisional_months: [],
  citation: '',
}

function rec(month: number, over: Partial<EntityMonth> = {}): EntityMonth {
  return {
    entity_type: 'COUNTRY',
    entity_id: 'XXX',
    entity_name: 'Testland',
    year: 2020,
    month,
    n_cells: 10,
    raw_by_witness: null,
    estimate: 100 + month,
    ci90_low: 90,
    ci90_high: 120,
    sd: 5,
    raw_combined_cell_days: 120,
    witnesses_used: ['AQUA_MODIS', 'SNPP_VIIRS'],
    n_witnesses: 2,
    disagreement_scale: 1,
    baseline_median: 50,
    baseline_p25: 20,
    baseline_p75: 60,
    pct_of_normal: 264.8,
    p_above: 0.9999,
    p_below: 0,
    p_within: 0,
    verdict: 'ABOVE_NORMAL',
    reason_codes: [],
    data_level: 'SP',
    method_version: '0.0.0-test',
    ...over,
  }
}

describe('sparkline', () => {
  it('the window is 12 months ending 3 after the selected one, within the record', () => {
    const w = sparkWindow({ year: 2020, month: 6 }, { year: 2002, month: 7 }, { year: 2026, month: 10 })
    expect(w).toHaveLength(12)
    expect(w[0]).toEqual({ year: 2019, month: 10 })
    expect(w[11]).toEqual({ year: 2020, month: 9 })
    const nearEnd = sparkWindow({ year: 2026, month: 10 }, { year: 2002, month: 7 }, { year: 2026, month: 10 })
    expect(nearEnd[11]).toEqual({ year: 2026, month: 10 })
    const nearStart = sparkWindow({ year: 2002, month: 8 }, { year: 2002, month: 7 }, { year: 2026, month: 10 })
    expect(nearStart[0]).toEqual({ year: 2002, month: 7 })
    expect(nearStart).toHaveLength(12)
  })
  const pts = (estimates: (number | null)[]): SparkPoint[] =>
    estimates.map((e, i) => ({ year: 2020, month: i + 1, estimate: e, p25: e === null ? null : 10, p75: e === null ? null : 50 }))
  it('a missing month breaks the line and is never drawn as zero', () => {
    const g = buildSpark(pts([10, 20, null, 30, 40]), 1, 100, 50, 0)
    expect(g.lines).toHaveLength(2)
    expect(g.dots).toHaveLength(0)
    expect(countGaps(pts([10, null, null]))).toBe(2)
    // a gap point has no band either
    expect(g.bands).toHaveLength(4)
  })
  it('a single isolated month is a dot, and the selected month is marked', () => {
    const g = buildSpark(pts([null, 10, null]), 1, 100, 50, 0)
    expect(g.lines).toHaveLength(0)
    expect(g.dots).toHaveLength(1)
    expect(g.marker).not.toBeNull()
    expect(buildSpark(pts([10, null]), 1, 100, 50, 0).marker).toBeNull()
  })
  it('the band spans the normal range: higher p75 is drawn higher than p25', () => {
    const g = buildSpark(pts([30, 30]), 0, 100, 100, 0)
    const b = g.bands[0]!
    expect(b.h).toBeGreaterThan(0)
    expect(b.y).toBeLessThan(b.y + b.h)
  })
  it('renders an accessible name, a text equivalent, the unit and a table', () => {
    const records = Array.from({ length: 12 }, (_, i) => rec(i + 1))
    records[4] = rec(5, { estimate: null, baseline_p25: null, baseline_p75: null })
    const html = renderToString(
      <Sparkline records={records} selected={{ year: 2020, month: 3 }} first={{ year: 2020, month: 1 }} latest={{ year: 2020, month: 12 }} areaName="Testland" />,
    )
    expect(html).toContain('role="img"')
    expect(html).toContain('Estimate by month for Testland, with the normal range as a band')
    expect(html).toContain('fire-active cell-days, Aqua-equivalent')
    expect(html).toContain('1 of 12 months have no data and are left as gaps.')
    expect(html).toContain('<table class="visually-hidden">')
    expect(html).toContain('spark-band')
    expect(html).toContain('spark-marker')
  })
})

describe('summary card', () => {
  const render = (records: EntityMonth[] | undefined, status: 'loading' | 'error' | 'ready' = 'ready', rawOnly = false) =>
    renderToString(
      <RawOnlyContext.Provider value={rawOnly}>
        <SummaryCard
          area={{ entity_type: 'COUNTRY', entity_id: 'XXX', entity_name: 'Testland' }}
          month={{ year: 2020, month: 3 }}
          status={status}
          records={records}
          meta={meta}
          headingRef={createRef()}
          download={<span>csv</span>}
        />
      </RawOnlyContext.Provider>,
    )
  const records = Array.from({ length: 12 }, (_, i) => rec(i + 1))
  it('shows the verdict with icon and label, the probability, the big % of normal, the numbers and the satellites', () => {
    const html = render(records)
    expect(html).toContain('Testland, March 2020')
    expect(html).toContain('Above normal')
    expect(html).toContain('▲')
    expect(html).toContain('More than 99% likely above normal.')
    expect(html).toContain('>265<')
    expect(html).toContain('103.0')
    expect(html).toContain('90.0 to 120.0')
    expect(html).toContain('Aqua MODIS, S-NPP VIIRS')
    expect(html).toContain(NO_CAVEATS_TEXT)
    expect(html).toContain('csv')
  })
  it('has a source line with the satellites, the data level, the method and the link to how the verdict is made', () => {
    const html = render(records)
    expect(html).toContain('Source: NASA FIRMS')
    expect(html).toContain('data level: standard (SP)')
    expect(html).toContain('method 0.0.0-test')
    expect(html).toContain(UI.SUMMARY_HOW_MADE)
    expect(html).toContain('#baseline-verdicts')
  })
  it('uses the approved reason texts and the provisional notice for near-real-time data', () => {
    const html = render([rec(3, { reason_codes: ['SINGLE_WITNESS'], data_level: 'NRT' }), ...records.filter((r) => r.month !== 3)])
    expect(html).toContain('Only one satellite contributed this month.')
    expect(html).toContain('Provisional')
    expect(html).toContain('data level: near-real-time (NRT)')
  })
  it('says no data for a missing estimate and % of normal, never zero', () => {
    const html = render([rec(3, { estimate: null, ci90_low: null, ci90_high: null, pct_of_normal: null, verdict: 'CANNOT_DETERMINE', p_above: null }), ...records.filter((r) => r.month !== 3)])
    expect(html).toContain('Cannot determine')
    expect(html).toContain('no data')
    expect(html).not.toContain('>0<')
  })
  it('shows loading, error and no-record states', () => {
    expect(render(undefined, 'loading')).toContain('Loading the summary')
    expect(render(undefined, 'error')).toContain('role="alert"')
    expect(render([], 'ready')).toContain('This area has no record for March 2020.')
  })
  it('does not show a verdict for a raw-only record', () => {
    const html = render([rec(3, { method_version: '0.1-raw-only', verdict: 'CANNOT_DETERMINE', pct_of_normal: null, p_above: null, baseline_p25: null, baseline_p75: null, estimate: null, ci90_low: null, ci90_high: null })], 'ready', true)
    expect(html).not.toContain('Cannot determine')
  })
  it('capitalises the probability sentence', () => {
    expect(sentence('more than 99% likely above normal')).toBe('More than 99% likely above normal')
  })
})

describe('header, chips, top anomalies', () => {
  it('has a text wordmark (no logo tile), the purpose line and the two links', () => {
    const html = renderToString(<Header showMethods onOpenMethods={() => {}} />)
    expect(html).toContain('<h1>Global Fire Harmonization</h1>')
    expect(html).toContain(UI.TAGLINE)
    expect(html).toContain(UI.NAV_METHODS)
    expect(html).toContain(UI.NAV_HOW_TO_READ)
    expect(html).toContain('aria-expanded="false"')
    expect(html).not.toContain('logo')
  })
  it('renders the featured stories as chips that say which one is selected', () => {
    const list = selectableStories()
    expect(list.length).toBeGreaterThan(0)
    const first = list[0]!
    const html = renderToString(<StoryChips areaId={first.entityId} month={{ year: first.year, month: first.month }} onChoose={() => {}} />)
    expect(html).toContain(storyLabel(first))
    expect(html).toContain('aria-pressed="true"')
    expect(FEATURED_STORIES.length).toBeGreaterThanOrEqual(list.length)
    expect(renderToString(<StoryChips stories={[]} areaId="" month={null} onChoose={() => {}} />)).toBe('')
  })
  it('lists at most five countries, in the given order, and links to the full list', () => {
    const above = Array.from({ length: 8 }, (_, i) => ({
      entity_type: 'COUNTRY' as const,
      entity_id: `C${i}`,
      entity_name: `Country ${i}`,
      verdict: 'ABOVE_NORMAL' as const,
      p_above: 0.9,
      p_below: 0,
      pct_of_normal: 300 - i,
    }))
    const html = renderToString(
      <TopAnomalies month={{ year: 2020, month: 3 }} status="ready" above={above} rawOnly={false} onSelect={() => {}} onSeeAll={() => {}} onRetry={() => {}} />,
    )
    expect(html.match(/<li>/g)?.length).toBe(5)
    expect(html).toContain('Biggest anomalies in March 2020')
    expect(html).toContain(UI.TOP_ANOMALIES_ALL)
    expect(html).not.toContain('Country 5')
  })
})
