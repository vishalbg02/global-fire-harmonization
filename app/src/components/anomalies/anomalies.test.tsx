import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { Anomaly } from '../../api/contract.ts'
import { parseAnomaly } from '../../api/contract.ts'
import { PROVISIONAL_NOTICE } from '../evidence/EvidenceBody.tsx'
import { ABOVE_HEADING, AnomalyPanel, BELOW_HEADING, EMPTY_MESSAGE } from './AnomalyPanel.tsx'
import type { AnomalyStatus } from './AnomalyPanel.tsx'
import {
  EXPANDED_SIZE,
  PAGE_SIZE,
  entryAriaLabel,
  entryProbability,
  notRankedCount,
  outlinedCountries,
  pctText,
  probabilityText,
  rankAnomalies,
  topN,
} from './rankings.ts'

// SYNTHETIC test data. Not NASA observations.
function anomaly(id: string, verdict: 'ABOVE_NORMAL' | 'BELOW_NORMAL', p: number | null, overrides: Record<string, unknown> = {}): Anomaly {
  return parseAnomaly({
    entity_type: 'COUNTRY',
    entity_id: id,
    entity_name: `Country ${id}`,
    verdict,
    p_above: verdict === 'ABOVE_NORMAL' ? p : 0,
    p_below: verdict === 'BELOW_NORMAL' ? p : 0,
    pct_of_normal: verdict === 'ABOVE_NORMAL' ? 250 : 40,
    ...overrides,
  })
}

// The API's order is by the larger probability; the app ranks per verdict itself.
const API_ORDER: Anomaly[] = [
  anomaly('AAA', 'BELOW_NORMAL', 0.99),
  anomaly('BBB', 'ABOVE_NORMAL', 0.97),
  anomaly('CCC', 'ABOVE_NORMAL', 0.99),
  anomaly('DDD', 'BELOW_NORMAL', 0.6),
  anomaly('EEE', 'ABOVE_NORMAL', 0.7),
  anomaly('ASI', 'ABOVE_NORMAL', 0.8, { entity_type: 'CONTINENT', entity_name: 'Asia' }),
  anomaly('GLOBAL', 'BELOW_NORMAL', 0.9, { entity_type: 'GLOBAL', entity_name: 'World' }),
]

describe('rankAnomalies', () => {
  it('ranks "above" by p_above and "below" by p_below, highest first', () => {
    const { above, below } = rankAnomalies(API_ORDER, 'COUNTRY')
    expect(above.map((a) => a.entity_id)).toEqual(['CCC', 'BBB', 'EEE'])
    expect(below.map((a) => a.entity_id)).toEqual(['AAA', 'DDD'])
  })

  it('keeps countries and continents apart, and leaves the world out of both', () => {
    const countries = rankAnomalies(API_ORDER, 'COUNTRY')
    const continents = rankAnomalies(API_ORDER, 'CONTINENT')
    expect(continents.above.map((a) => a.entity_id)).toEqual(['ASI'])
    expect(continents.below).toEqual([])
    for (const list of [countries.above, countries.below, continents.above, continents.below]) {
      expect(list.some((a) => a.entity_type === 'GLOBAL')).toBe(false)
    }
  })

  it('breaks ties by id and puts an entry without a probability last', () => {
    const tied = [anomaly('ZZZ', 'ABOVE_NORMAL', 0.9), anomaly('AAA', 'ABOVE_NORMAL', 0.9), anomaly('MMM', 'ABOVE_NORMAL', null)]
    expect(rankAnomalies(tied, 'COUNTRY').above.map((a) => a.entity_id)).toEqual(['AAA', 'ZZZ', 'MMM'])
  })

  it('does not change its input', () => {
    const copy = [...API_ORDER]
    rankAnomalies(API_ORDER, 'COUNTRY')
    expect(API_ORDER).toEqual(copy)
  })

  it('returns two empty rankings for no anomalies', () => {
    expect(rankAnomalies([], 'COUNTRY')).toEqual({ above: [], below: [] })
  })
})

describe('entry text', () => {
  it('uses the stored probability that belongs to the verdict, in whole percentages', () => {
    expect(entryProbability(anomaly('A', 'ABOVE_NORMAL', 0.824))).toBe(0.824)
    expect(probabilityText(anomaly('A', 'ABOVE_NORMAL', 0.824))).toBe('82% likely above normal')
    expect(probabilityText(anomaly('B', 'BELOW_NORMAL', 0.995))).toBe('100% likely below normal')
    expect(probabilityText(anomaly('C', 'ABOVE_NORMAL', null))).toBeNull()
  })

  it('shows % of normal as stored and null as "no data", never zero', () => {
    expect(pctText(anomaly('A', 'ABOVE_NORMAL', 0.9, { pct_of_normal: 704.08 }))).toBe('704% of normal')
    expect(pctText(anomaly('A', 'ABOVE_NORMAL', 0.9, { pct_of_normal: null }))).toBe('no data')
    expect(pctText(anomaly('A', 'ABOVE_NORMAL', 0.9, { pct_of_normal: 0 }))).toBe('0% of normal')
  })

  it('builds an accessible label with rank, area, probability and percentage', () => {
    expect(entryAriaLabel(2, anomaly('IDN', 'ABOVE_NORMAL', 0.95, { entity_name: 'Indonesia' }))).toBe(
      'Rank 2, Indonesia, 95% likely above normal, 250% of normal',
    )
  })
})

describe('counts, limits and outlines', () => {
  it('takes the top N without changing the order', () => {
    expect(topN([1, 2, 3, 4], 2)).toEqual([1, 2])
    expect(topN([1], 10)).toEqual([1])
    expect([PAGE_SIZE, EXPANDED_SIZE]).toEqual([10, 20])
  })

  it('counts the areas in neither ranking, and never goes below zero', () => {
    const r = rankAnomalies(API_ORDER, 'COUNTRY') // 3 above + 2 below
    expect(notRankedCount(12, r)).toBe(7)
    expect(notRankedCount(5, r)).toBe(0)
    expect(notRankedCount(2, r)).toBe(0)
  })

  it('outlines only the listed countries, split by verdict', () => {
    const r = rankAnomalies(API_ORDER, 'COUNTRY')
    expect(outlinedCountries(topN(r.above, 2), topN(r.below, 1))).toEqual({ above: ['CCC', 'BBB'], below: ['AAA'] })
  })

  it('outlines no continent and no world (they have no polygon on the map)', () => {
    const r = rankAnomalies(API_ORDER, 'CONTINENT')
    expect(outlinedCountries(r.above, r.below)).toEqual({ above: [], below: [] })
  })
})

const panel = (overrides: Partial<Parameters<typeof AnomalyPanel>[0]> = {}, status: AnomalyStatus = 'ready') =>
  renderToString(
    <AnomalyPanel
      month={{ year: 2015, month: 9 }}
      provisional={false}
      status={status}
      onRetry={() => {}}
      tab="COUNTRY"
      onTabChange={() => {}}
      expanded={false}
      onToggleExpanded={() => {}}
      rankings={rankAnomalies(API_ORDER, 'COUNTRY')}
      totalAreas={12}
      onSelect={() => {}}
      {...overrides}
    />,
  )

describe('AnomalyPanel', () => {
  it('names the month and has Countries and Continents tabs, Countries selected', () => {
    const html = panel()
    expect(html).toContain('Anomalies in September 2015')
    expect(html).toContain('role="tablist"')
    expect(html).toMatch(/aria-selected="true"[^>]*>Countries</)
    expect(html).toMatch(/aria-selected="false"[^>]*>Continents</)
  })

  it('shows two rankings with the Lead-specified headings', () => {
    const html = panel()
    expect(html).toContain(ABOVE_HEADING)
    expect(html).toContain(BELOW_HEADING)
    expect(ABOVE_HEADING).toBe('Most likely above normal')
    expect(BELOW_HEADING).toBe('Most likely below normal')
  })

  it('shows each entry as a button with rank, area, verdict icon and label, probability and percentage', () => {
    const html = panel()
    expect(html.match(/class="anomaly-entry"/g)).toHaveLength(5)
    expect(html).toContain('aria-label="Rank 1, Country CCC, 99% likely above normal, 250% of normal"')
    expect(html).toContain('▲ Above normal, 99% likely above normal, 250% of normal')
    expect(html).toContain('▼ Below normal, 99% likely below normal, 40% of normal')
  })

  it('lists entries in the ranked order, highest probability first', () => {
    const html = panel()
    expect(html.indexOf('Country CCC')).toBeLessThan(html.indexOf('Country BBB'))
    expect(html.indexOf('Country BBB')).toBeLessThan(html.indexOf('Country EEE'))
  })

  it('never shows a verdict that is not ranked, and never a ranking of the world', () => {
    const html = panel()
    for (const hidden of ['Cannot determine', 'No detected activity', 'Within normal', 'World']) {
      expect(html).not.toContain(hidden)
    }
  })

  it('says how many areas are in neither ranking, without claiming they are all undeterminable', () => {
    const html = panel()
    expect(html).toContain('7 of 12 countries are in neither ranking')
    expect(html).toContain('within normal, cannot be determined, or no activity was detected')
    expect(panel({ totalAreas: null })).not.toContain('in neither ranking')
  })

  it('shows "Show more" only when a ranking is longer than 10, and "Show fewer" once expanded', () => {
    expect(panel()).not.toContain('Show more')
    const many = Array.from({ length: 12 }, (_, i) => anomaly(`C${String(i).padStart(2, '0')}`, 'ABOVE_NORMAL', 0.9 - i / 100))
    const r = rankAnomalies(many, 'COUNTRY')
    const collapsed = panel({ rankings: r })
    expect(collapsed).toContain('Show more')
    expect(collapsed.match(/class="anomaly-entry"/g)).toHaveLength(10)
    const expanded = panel({ rankings: r, expanded: true })
    expect(expanded).toContain('Show fewer')
    expect(expanded.match(/class="anomaly-entry"/g)).toHaveLength(12)
  })

  it('says "None this month." for a ranking with no entries when the other has some', () => {
    const onlyAbove = rankAnomalies([anomaly('AAA', 'ABOVE_NORMAL', 0.9)], 'COUNTRY')
    expect(panel({ rankings: onlyAbove })).toContain('None this month.')
  })

  it('shows the exact empty message when neither ranking has an entry', () => {
    const html = panel({ rankings: { above: [], below: [] } })
    expect(html).toContain('No areas with a confident above- or below-normal verdict this month.')
    expect(EMPTY_MESSAGE).toBe('No areas with a confident above- or below-normal verdict this month.')
    expect(html).not.toContain('Most likely')
  })

  it('shows loading, an error with retry, and a prompt when no month is chosen', () => {
    expect(panel({}, 'loading')).toContain('Loading the anomalies')
    const error = panel({}, 'error')
    expect(error).toContain('Data are not available right now.')
    expect(error).toContain('Retry')
    expect(error).toContain('role="alert"')
    const idle = panel({ month: null }, 'idle')
    expect(idle).toContain('Choose a month to see the anomalies.')
    expect(idle).toContain('<h2>Anomalies</h2>')
    expect(idle).not.toContain('Most likely')
  })

  it('shows the provisional notice with the evidence panel wording for a provisional month only', () => {
    expect(panel({ provisional: true })).toContain(PROVISIONAL_NOTICE)
    expect(PROVISIONAL_NOTICE).toBe('Provisional: may change when science-quality data arrive')
    expect(panel({ provisional: false })).not.toContain(PROVISIONAL_NOTICE)
  })

  it('shows the Continents tab as selected, with its own count wording', () => {
    const html = panel({ tab: 'CONTINENT', rankings: rankAnomalies(API_ORDER, 'CONTINENT'), totalAreas: 6 })
    expect(html).toMatch(/aria-selected="true"[^>]*>Continents</)
    expect(html).toContain('Country ASI'.replace('Country ASI', 'Asia'))
    expect(html).toContain('5 of 6 continents are in neither ranking')
  })
})
