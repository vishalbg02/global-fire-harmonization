import { createRef } from 'react'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { REASON_CODES } from '../../api/contract.ts'
import type { EntityMonth, Metadata, ReasonCode } from '../../api/contract.ts'
import { PROVISIONAL_MARK, WHY_HEADING } from '../../content/answer.ts'
import { NO_CAVEATS_TEXT } from '../../content/evidenceText.ts'
import { REASON_CODE_SHORT } from '../../content/reasonCodes.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { ReasonChip, ReasonChips } from './ReasonChips.tsx'
import { toggleReason } from './reasonChips.ts'
import { SummaryCard } from './SummaryCard.tsx'

// SYNTHETIC test data. Not NASA observations.
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

const records = Array.from({ length: 12 }, (_, i) => rec(i + 1))
const withMarch = (over: Partial<EntityMonth>) => [rec(3, over), ...records.filter((r) => r.month !== 3)]
const card = (list: EntityMonth[] | undefined, status: 'loading' | 'error' | 'ready' = 'ready', extra: Record<string, unknown> = {}) =>
  renderToString(
    <SummaryCard
      area={{ entity_type: 'COUNTRY', entity_id: 'XXX', entity_name: 'Testland' }}
      month={{ year: 2020, month: 3 }}
      status={status}
      records={list}
      meta={meta}
      headingRef={createRef()}
      download={<span>csv</span>}
      copyLink={<span>copy</span>}
      onCompare={() => {}}
      onDetails={() => {}}
      {...extra}
    />,
  )
const count = (html: string, text: string) => html.split(text).length - 1
const plain = (html: string) => html.replace(/<[^>]+>/g, '').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&')

describe('reason chips', () => {
  it('toggles one chip and leaves the others as they are', () => {
    expect(toggleReason([], 'WIDE_INTERVAL')).toEqual(['WIDE_INTERVAL'])
    expect(toggleReason(['WIDE_INTERVAL', 'SINGLE_WITNESS'], 'WIDE_INTERVAL')).toEqual(['SINGLE_WITNESS'])
    expect(toggleReason(['SINGLE_WITNESS'], 'OUTAGE')).toEqual(['SINGLE_WITNESS', 'OUTAGE'])
  })

  it('a closed chip shows the short label, says it is collapsed and keeps its sentence hidden', () => {
    for (const code of REASON_CODES) {
      const html = renderToString(
        <ul>
          <ReasonChip code={code} open={false} onToggle={() => {}} idBase="t" />
        </ul>,
      )
      expect(html).toContain(REASON_CODE_SHORT[code].replace(/'/g, '&#x27;'))
      expect(html).toContain('aria-expanded="false"')
      expect(html).toContain(`aria-controls="t-${code}"`)
      expect(html).toMatch(new RegExp(`id="t-${code}"[^>]*hidden=""`))
    }
  })

  it('an open chip shows the approved sentence and its "Learn more" link to the methods section', () => {
    for (const code of REASON_CODES) {
      const html = renderToString(
        <ul>
          <ReasonChip code={code} open onToggle={() => {}} idBase="t" />
        </ul>,
      )
      expect(html).toContain('aria-expanded="true"')
      expect(html).not.toMatch(new RegExp(`id="t-${code}"[^>]*hidden`))
      expect(plain(html)).toContain(REASON_TEXTS[code])
      expect(html).toContain(`#reason-${code}"`)
      expect(html).toContain('page=methods')
      expect(plain(html)).toContain('Learn more')
    }
  })

  it('lists every stored code once, in the stored order, under "Why", with the tour anchor', () => {
    const codes: ReasonCode[] = ['AQUA_DRIFT_ERA', 'PROVISIONAL_NRT', 'WIDE_INTERVAL']
    const html = renderToString(<ReasonChips codes={codes} />)
    expect(html).toContain('data-tour="why"')
    expect(plain(html)).toContain(WHY_HEADING)
    const positions = codes.map((c) => html.indexOf(REASON_CODE_SHORT[c]))
    expect(positions.every((p) => p > 0)).toBe(true)
    expect([...positions].sort((a, b) => a - b)).toEqual(positions)
    expect(count(html, 'aria-expanded="false"')).toBe(3)
    expect(html).not.toContain(NO_CAVEATS_TEXT)
  })

  it('opens the chips it is asked to open, and says "no caveat flags" when there is no code', () => {
    const html = renderToString(<ReasonChips codes={['SINGLE_WITNESS', 'WIDE_INTERVAL']} initialOpen={['WIDE_INTERVAL']} />)
    expect(count(html, 'aria-expanded="true"')).toBe(1)
    expect(count(html, 'aria-expanded="false"')).toBe(1)
    const none = renderToString(<ReasonChips codes={[]} />)
    expect(none).toContain(NO_CAVEATS_TEXT)
    expect(none).toContain('data-tour="why"')
  })
})

describe('answer card hierarchy (T-093)', () => {
  it('reads in order: heading, verdict, % of normal, probability, interval bar, sparkline, Why, source, actions', () => {
    const html = card(records)
    const order = ['Testland, March 2020', 'Above normal', '>265<', 'More than 99% likely above normal.', 'class="ibar"', 'class="spark"', 'data-tour="why"', 'Source: NASA FIRMS', 'class="summary-actions"']
    const at = order.map((t) => html.indexOf(t))
    expect(at.every((p) => p >= 0)).toBe(true)
    expect([...at].sort((a, b) => a - b)).toEqual(at)
  })

  it('writes the % of normal unit in its own quieter element, with the explainers of the terms shown', () => {
    const html = card(records)
    expect(html).toContain('<span class="big-value">265</span><small>% of normal</small>')
    expect(html).toContain('What is % of normal?')
    expect(html).toContain('What is probability?')
    expect(html).toContain('What is 90% interval?')
  })

  it('shows the estimate, the interval and the satellites once each on screen', () => {
    // The sparkline's table for screen readers (visually hidden) repeats every month's estimate; it is left out here.
    const html = card(records).replace(/<table class="visually-hidden">.*?<\/table>/s, '')
    expect(count(html, '>103.0<')).toBe(1)
    expect(count(html, '>90.0 to 120.0<')).toBe(1)
    expect(count(plain(html), 'Aqua MODIS, S-NPP VIIRS')).toBe(1)
  })

  it('shows the provisional notice once for a near-real-time month, and none for a standard one', () => {
    const nrt = card(withMarch({ data_level: 'NRT', reason_codes: ['PROVISIONAL_NRT'] }))
    expect(count(nrt, 'class="provisional-mark"')).toBe(1)
    expect(plain(nrt)).toContain(`${PROVISIONAL_MARK}`)
    expect(nrt).toContain('What is provisional?')
    // The old separate notice line is gone; the stored reason stays a chip under "Why".
    expect(nrt).not.toContain('evidence-provisional')
    expect(nrt).toContain(REASON_CODE_SHORT.PROVISIONAL_NRT)
    expect(card(records)).not.toContain('provisional-mark')
  })

  it('states "Cannot determine" as a result: its approved sentence and explainer, and no alert', () => {
    const html = card(withMarch({ verdict: 'CANNOT_DETERMINE', p_above: 0.4, p_below: 0.1, p_within: 0.5, reason_codes: ['WIDE_INTERVAL'] }))
    expect(html).toContain(VERDICT_PRESENTATION.CANNOT_DETERMINE.label)
    expect(plain(html)).toContain(VERDICT_PRESENTATION.CANNOT_DETERMINE.description)
    expect(html).toContain('What is cannot determine?')
    expect(html).not.toContain('role="alert"')
    expect(html).not.toContain('state-error')
  })

  it('states "No detected activity" as a result too', () => {
    const html = card(withMarch({ verdict: 'NO_DETECTED_ACTIVITY', p_above: null, p_below: null, p_within: null, pct_of_normal: null }))
    expect(plain(html)).toContain(VERDICT_PRESENTATION.NO_DETECTED_ACTIVITY.description)
    expect(html).toContain('What is no detected activity?')
    expect(html).not.toContain('role="alert"')
  })

  it('has the four actions in one group, and the story card after them when a story is on screen', () => {
    const html = card(records)
    expect(html).toContain('role="group"')
    expect(html).toContain('csv')
    expect(html).toContain('copy')
    expect(html).toContain('Compare with…')
    expect(html).toContain('>Details<')
    expect(html).not.toContain('story-card')
  })

  it('shows a skeleton with a spoken loading message while the series loads, and no spinner in the text', () => {
    const html = card(undefined, 'loading')
    expect(html).toContain('class="skeleton summary-skeleton" role="status"')
    expect(html).toContain('Loading the summary…')
    expect(html).toContain('aria-busy="true"')
    expect(count(html, 'class="skeleton-block"')).toBeGreaterThan(8)
    expect(html).not.toContain('class="verdict"')
  })

  it('says what went wrong in plain words, with Retry when it can help', () => {
    const html = card(undefined, 'error', { onRetry: () => {} })
    expect(html).toContain('role="alert"')
    expect(html).toContain('Data are not available right now. The summary could not be loaded.')
    expect(html).toContain('>Retry<')
  })
})
