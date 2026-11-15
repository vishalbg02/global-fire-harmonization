import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { parseEntityMonth } from '../../api/contract.ts'
import type { EntityMonth, Metadata } from '../../api/contract.ts'
import * as T from '../../content/timeline.ts'
import * as UI from '../../content/ui.ts'
import { monthKey, monthRange, offlineMapMonths } from '../../state/months.ts'
import { Timeline } from './Timeline.tsx'

// SYNTHETIC metadata and series with the shape of the record. Not NASA observations.
const META: Metadata = {
  contract_version: '0.1.1', method_version: '0.1.0', synthetic: true, first_month: '2002-07', latest_month: '2026-11',
  provisional_months: ['2026-08', '2026-09', '2026-10', '2026-11'], citation: 'SYNTHETIC',
}
const ALL = monthRange(META.first_month, META.latest_month, META.provisional_months)
const noop = () => {}

function rec(year: number, month: number, estimate: number | null): EntityMonth {
  return parseEntityMonth({
    entity_type: 'GLOBAL', entity_id: 'GLOBAL', entity_name: 'World', year, month, n_cells: 1, raw_by_witness: null,
    estimate, ci90_low: null, ci90_high: null, sd: null, raw_combined_cell_days: 3, witnesses_used: ['AQUA_MODIS'],
    n_witnesses: 1, disagreement_scale: null, baseline_median: null, baseline_p25: null, baseline_p75: null,
    pct_of_normal: null, p_above: null, p_below: null, p_within: null, verdict: 'CANNOT_DETERMINE', reason_codes: [],
    data_level: 'SP', method_version: '0.1.0',
  })
}
// Nulls at the first three months and the latest month, as the stored world series has.
const SERIES = ALL.map((m, i) => rec(m.year, m.month, i < 3 || i === ALL.length - 1 ? null : 1 + (i % 12)))

const render = (props: Partial<Parameters<typeof Timeline>[0]> = {}) =>
  renderToString(<Timeline months={ALL} value={{ year: 2015, month: 9 }} onChange={noop} meta={META} {...props} />)

describe('Timeline (T-093)', () => {
  it('is an ARIA slider whose value is the month, with the key hint and the satellite joins read out', () => {
    const html = render()
    expect(html).toContain('role="slider"')
    expect(html).toContain('tabindex="0"')
    expect(html).toContain(`aria-label="${T.SLIDER_LABEL}"`)
    expect(html).toContain('aria-valuetext="September 2015"')
    expect(html).toContain('aria-valuemin="0"')
    expect(html).toContain(`aria-valuemax="${ALL.length - 1}"`)
    expect(html).toContain(`aria-valuenow="${ALL.findIndex((m) => m.year === 2015 && m.month === 9)}"`)
    expect(html).toContain('Satellite joins: S-NPP VIIRS in January 2012; NOAA-20 VIIRS in April 2018.')
  })

  it('marks the current month with its name, the year in Mono', () => {
    expect(render()).toMatch(/class="tl-flag[^"]*"[^>]*>September(<!-- -->)? <span class="tl-year">2015<\/span>/)
  })

  it('says "provisional" in the value of a provisional month, and shades and labels the provisional months', () => {
    const html = render({ value: { year: 2026, month: 10 } })
    expect(html).toContain('aria-valuetext="October 2026, provisional"')
    expect(html).toContain('class="tl-span tl-prov"')
    expect(html).toContain(`>${T.PROVISIONAL}<`)
    expect(html).toMatch(/class="bare help-tip" aria-label="What is provisional\?"/)
  })

  it('draws the series behind the strip with gaps for null values (one run between the nulls)', () => {
    const html = render({ series: SERIES })
    expect((html.match(/<polyline /g) ?? []).length).toBe(1)
    const points = /<polyline points="([^"]+)"/.exec(html)![1]!.split(' ')
    expect(points).toHaveLength(ALL.length - 4)
    expect(html).toContain(T.LINE_HARMONIZED)
  })

  it('shows the strip without the line while the series loads, and names the raw line in the raw view', () => {
    const loading = render({ series: undefined })
    expect(loading).not.toContain('<polyline')
    expect(loading).toContain('class="tl-track"')
    expect(loading).toContain(T.LINE_LOADING)
    expect(render({ series: SERIES, source: 'raw' })).toContain(T.LINE_RAW)
  })

  it('takes the play state from outside: Pause while playing, Play when paused', () => {
    const on = render({ playing: true, onPlayingChange: noop })
    expect(on).toContain(`aria-label="${UI.PAUSE_LABEL}"`)
    expect(on).toContain('aria-pressed="true"')
    const off = render({ playing: false, onPlayingChange: noop })
    expect(off).toContain(`aria-label="${UI.PLAY_LABEL}"`)
    expect(off).toContain('aria-pressed="false"')
  })

  it('dims months without a map and reads "no offline map" for a month that has none', () => {
    const last24 = offlineMapMonths(ALL, ALL.slice(-24).map((m) => monthKey(m.year, m.month)))
    const html = render({ months: last24, value: { year: 2010, month: 3 } })
    expect(html).toContain('class="tl-span tl-missing"')
    expect(html).toContain('aria-valuetext="March 2010, no offline map"')
    expect(html).toContain('March 2010 (no offline map)')
    expect(html).toContain('aria-valuemax="23"')
  })

  it('keeps the strip and its labels when the metadata is not loaded yet', () => {
    const html = renderToString(<Timeline months={[]} value={null} onChange={noop} />)
    expect(html).toContain('class="tl-strip is-empty"')
    expect(html).toContain('aria-valuetext="No month available"')
    expect(html).toContain('tabindex="-1"')
  })
})
