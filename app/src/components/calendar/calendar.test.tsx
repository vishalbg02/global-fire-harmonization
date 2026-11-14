import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ContractError, VERDICTS, parseEntityMonth } from '../../api/contract.ts'
import type { EntityMonth } from '../../api/contract.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { CalendarLegend } from './CalendarLegend.tsx'
import { CalendarTable } from './CalendarTable.tsx'
import { ValueModeSelector } from './ValueModeSelector.tsx'
import { buildChartOption, buildHeatPoints } from './chartOption.ts'
import { buildCalendarGrid, maxEstimate } from './grid.ts'
import {
  NO_DATA_RGB,
  OUTSIDE_RGB,
  PCT_CENTRE,
  cellVisual,
  contrastRatio,
  divergingRgb,
  readableText,
  sequentialRgb,
  toCss,
} from './scales.ts'
import { cellAriaLabel, cellLines, escapeHtml, provisionalNote, tooltipHtml } from './text.ts'

// SYNTHETIC test data. Not NASA observations.
function record(year: number, month: number, overrides: Record<string, unknown> = {}): EntityMonth {
  return parseEntityMonth({
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    year,
    month,
    n_cells: 10,
    raw_by_witness: null,
    estimate: 12.34,
    ci90_low: 8.1,
    ci90_high: 16.4,
    sd: 2,
    raw_combined_cell_days: 20,
    witnesses_used: ['SNPP_VIIRS'],
    n_witnesses: 1,
    disagreement_scale: null,
    baseline_median: 9,
    baseline_p25: 6,
    baseline_p75: 12,
    pct_of_normal: 137,
    p_above: 0.82,
    p_below: 0.02,
    p_within: 0.16,
    verdict: 'ABOVE_NORMAL',
    reason_codes: [],
    data_level: 'SP',
    method_version: 'synthetic-test',
    ...overrides,
  })
}

// A record for 2002-08, 2003-01 (null value) and 2003-02 (provisional), inside 2002-07 to 2003-03.
const RECORDS = [
  record(2002, 8),
  record(2003, 1, { pct_of_normal: null, estimate: null, ci90_low: null, ci90_high: null, verdict: 'CANNOT_DETERMINE', p_above: null, p_below: null, p_within: null }),
  record(2003, 2, { data_level: 'NRT', reason_codes: ['PROVISIONAL_NRT'] }),
]
const ROWS = buildCalendarGrid(RECORDS, '2002-07', '2003-03', ['2003-03'])

describe('buildCalendarGrid', () => {
  it('has one row per year from the first to the latest year, with 12 months each', () => {
    expect(ROWS.map((r) => r.year)).toEqual([2002, 2003])
    expect(ROWS.every((r) => r.cells.length === 12)).toBe(true)
  })

  it('marks months outside the record as outside, never as zero', () => {
    const cells2002 = ROWS[0].cells
    expect(cells2002.slice(0, 6).every((c) => c.kind === 'outside' && c.record === null)).toBe(true) // Jan-Jun 2002
    expect(cells2002[6].kind).toBe('no-record') // Jul 2002: inside the record, no record stored
    expect(cells2002[7].kind).toBe('record') // Aug 2002
    expect(ROWS[1].cells.slice(3).every((c) => c.kind === 'outside')).toBe(true) // after Mar 2003
  })

  it('marks a month inside the record with no stored record as no-record (no data)', () => {
    expect(ROWS[1].cells[2].kind).toBe('no-record') // Mar 2003 has no record
  })

  it('marks provisional months from the metadata list and from data_level', () => {
    expect(ROWS[1].cells[2].provisional).toBe(true) // listed in provisional_months
    expect(ROWS[1].cells[1].provisional).toBe(true) // data_level NRT
    expect(ROWS[0].cells[7].provisional).toBe(false)
    expect(ROWS[0].cells[0].provisional).toBe(false) // outside the record is never provisional
  })

  it('rejects two records for the same month', () => {
    expect(() => buildCalendarGrid([record(2003, 1), record(2003, 1)], '2002-07', '2003-03', [])).toThrow(
      ContractError,
    )
  })

  it('finds the largest harmonized estimate and ignores null', () => {
    expect(maxEstimate([record(2003, 1, { estimate: null }), record(2003, 2, { estimate: 40 })])).toBe(40)
    expect(maxEstimate([record(2003, 1, { estimate: null })])).toBe(0)
  })
})

describe('diverging scale for % of normal', () => {
  it('is the neutral colour at 100%, blue below and vermillion above', () => {
    const [r, g, b] = divergingRgb(PCT_CENTRE)
    expect(r).toBeGreaterThan(240)
    expect(g).toBeGreaterThan(240)
    expect(b).toBeGreaterThan(240)
    expect(divergingRgb(0)[2]).toBeGreaterThan(divergingRgb(0)[0]) // blue end
    expect(divergingRgb(200)[0]).toBeGreaterThan(divergingRgb(200)[2]) // vermillion end
  })

  it('is symmetric in construction: 50% and 150% sit between the neutral and their end colour', () => {
    expect(divergingRgb(50)).not.toEqual(divergingRgb(0))
    expect(divergingRgb(50)).not.toEqual(divergingRgb(100))
    expect(divergingRgb(150)).not.toEqual(divergingRgb(200))
    expect(divergingRgb(150)).not.toEqual(divergingRgb(100))
  })

  it('clamps colour at 0% and 200% while the true value stays available', () => {
    expect(divergingRgb(-50)).toEqual(divergingRgb(0))
    expect(divergingRgb(704)).toEqual(divergingRgb(200))
    expect(tooltipHtml(ROWS[0].cells[7])).toContain('137% of normal')
    const big = buildCalendarGrid([record(2002, 8, { pct_of_normal: 704 })], '2002-07', '2002-12', [])
    expect(tooltipHtml(big[0].cells[7])).toContain('704% of normal')
  })

  it('keeps text readable (WCAG AA, contrast at least 4.5) at every step of the ramp', () => {
    for (let pct = 0; pct <= 200; pct += 5) {
      const bg = divergingRgb(pct)
      expect(contrastRatio(bg, readableText(bg))).toBeGreaterThanOrEqual(4.5)
    }
    for (let t = 0; t <= 1; t += 0.05) {
      const bg = sequentialRgb(t * 100, 100)
      expect(contrastRatio(bg, readableText(bg))).toBeGreaterThanOrEqual(4.5)
    }
    expect(contrastRatio(NO_DATA_RGB, readableText(NO_DATA_RGB))).toBeGreaterThanOrEqual(4.5)
  })

  it('computes the WCAG contrast ratio correctly at the extremes', () => {
    expect(contrastRatio([0, 0, 0], [255, 255, 255])).toBeCloseTo(21, 5)
    expect(contrastRatio([128, 128, 128], [128, 128, 128])).toBeCloseTo(1, 5)
  })
})

describe('cellVisual', () => {
  it('shows null as the no-data colour in both modes, never as the low end of a ramp', () => {
    const none = record(2003, 1, { pct_of_normal: null, estimate: null })
    expect(cellVisual(none, 'pct', 50).color).toEqual(NO_DATA_RGB)
    expect(cellVisual(none, 'activity', 50).color).toEqual(NO_DATA_RGB)
    expect(cellVisual(none, 'pct', 50).value).toBeNull()
  })

  it('treats a real zero as a value, not as no data', () => {
    const zero = record(2003, 1, { estimate: 0 })
    expect(cellVisual(zero, 'activity', 50).color).not.toEqual(NO_DATA_RGB)
    expect(cellVisual(zero, 'activity', 50).value).toBe(0)
  })

  it('colours by the mode and gives the verdict icon in both modes', () => {
    const r = record(2003, 1)
    expect(cellVisual(r, 'pct', 50).color).toEqual(divergingRgb(137))
    expect(cellVisual(r, 'activity', 50).color).toEqual(sequentialRgb(12.34, 50))
    expect(cellVisual(r, 'pct', 50).icon).toBe('▲')
    expect(cellVisual(r, 'activity', 50).icon).toBe('▲')
  })

  it('gives every verdict its own icon', () => {
    const icons = VERDICTS.map((verdict) => cellVisual(record(2003, 1, { verdict }), 'pct', 50).icon)
    expect(new Set(icons).size).toBe(VERDICTS.length)
    for (const v of VERDICTS) expect(icons).toContain(VERDICT_PRESENTATION[v].icon)
  })
})

describe('tooltip and labels', () => {
  it('describes a record: verdict with probability, value, interval, units and notes', () => {
    const text = cellLines(ROWS[0].cells[7]).join('\n')
    expect(text).toContain('Aug 2002')
    expect(text).toContain('▲ Above normal, 82% likely above normal')
    expect(text).toContain('137% of normal')
    expect(text).toContain('90% interval 8.1 to 16.4')
    expect(text).toContain('fire-active cell-days')
  })

  it('shows "no data" for a null value and never 0', () => {
    const text = cellLines(ROWS[1].cells[0]).join('\n')
    expect(text).toContain('no data')
    expect(text).toContain('Cannot determine')
    expect(text).not.toContain('0% of normal')
  })

  it('says "Provisional (NRT)" for an NRT month and plain "Provisional" for a listed one', () => {
    expect(provisionalNote(ROWS[1].cells[1])).toBe('Provisional (NRT)')
    expect(provisionalNote(ROWS[1].cells[2])).toBe('Provisional')
    expect(provisionalNote(ROWS[0].cells[7])).toBeNull()
    expect(cellLines(ROWS[1].cells[1]).join('\n')).toContain('Provisional (NRT)')
  })

  it('describes outside-record and no-record months without a value', () => {
    expect(cellLines(ROWS[0].cells[0]).join('\n')).toContain('Outside the record')
    expect(cellLines(ROWS[1].cells[2]).join('\n')).toContain('No data')
    expect(cellAriaLabel(ROWS[0].cells[0])).toContain('Jan 2002')
  })

  it('escapes text in the tooltip HTML', () => {
    expect(escapeHtml('<b>"x" & \'y\'</b>')).toBe('&lt;b&gt;&quot;x&quot; &amp; &#39;y&#39;&lt;/b&gt;')
    expect(tooltipHtml(ROWS[0].cells[7])).not.toContain('<script')
  })
})

describe('chart option', () => {
  const points = buildHeatPoints(ROWS, 'pct', 20, { year: 2002, month: 8 })

  it('has one point per calendar cell: years x 12 months', () => {
    expect(points).toHaveLength(2 * 12)
  })

  it('draws outside-record months white with no icon, and no-data months grey', () => {
    expect(points[0].itemStyle.color).toBe(toCss(OUTSIDE_RGB))
    expect(points[0].label.show).toBe(false)
    expect(points[12 + 2].itemStyle.color).toBe(toCss(NO_DATA_RGB)) // Mar 2003, no record
  })

  it('gives every record cell its verdict icon', () => {
    expect(points[7].label.formatter).toBe('▲')
    expect(points[12].label.formatter).toBe('?') // CANNOT_DETERMINE
    expect(points[12].itemStyle.color).toBe(toCss(NO_DATA_RGB)) // null pct is no data
  })

  it('outlines provisional months with a dashed border and the selected month with a solid one', () => {
    expect(points[12 + 1].itemStyle.borderType).toBe('dashed') // Feb 2003, NRT
    expect(points[7].itemStyle.borderColor).toBe('#0050c8') // selected: Aug 2002
    expect(points[7].itemStyle.borderType).toBe('solid')
    expect(points[7].itemStyle.borderWidth).toBe(3)
  })

  it('builds an option with accessibility on, animation off and years top to bottom', () => {
    const option = buildChartOption(ROWS, 'pct', 20, null, 'Indonesia') as Record<string, unknown>
    expect(option.animation).toBe(false)
    expect((option.aria as { enabled: boolean }).enabled).toBe(true)
    expect(JSON.stringify(option)).toContain('Indonesia')
    expect((option.yAxis as { inverse: boolean }).inverse).toBe(true)
  })
})

describe('CalendarTable (accessible table view)', () => {
  const html = (mode: 'pct' | 'activity') =>
    renderToString(
      <CalendarTable rows={ROWS} mode={mode} maxActivity={20} selected={{ year: 2002, month: 8 }} areaName="Indonesia" onSelectMonth={() => {}} />,
    )

  it('is a table with a caption, column headers for the months and row headers for the years', () => {
    const out = html('pct')
    expect(out).toContain('<caption>')
    expect(out).toContain('scope="col"')
    expect(out).toContain('scope="row"')
    expect(out).toContain('Jan')
    expect(out).toContain('2002')
  })

  it('shows the same values as the chart in each mode', () => {
    expect(html('pct')).toContain('137%')
    expect(html('activity')).toContain('12.3')
  })

  it('has a button with a full label for every record cell, so the keyboard can reach the data', () => {
    const out = html('pct')
    expect(out.match(/<button/g)).toHaveLength(RECORDS.length)
    expect(out).toContain('aria-label="Aug 2002. ▲ Above normal')
    expect(out).toContain('aria-pressed="true"')
  })

  it('shows no data for null and "outside the record" for months outside it', () => {
    const out = html('pct')
    expect(out).toContain('no data')
    expect(out).toContain('Outside the record')
  })
})

describe('CalendarLegend and ValueModeSelector', () => {
  it('shows the diverging scale centred on 100% in % of normal mode, with the clamp stated', () => {
    const out = renderToString(<CalendarLegend mode="pct" maxActivity={20} />)
    expect(out).toContain('100% (normal level)')
    expect(out).toContain('200% or more')
    expect(out).toContain('tooltips show the true value')
  })

  it('shows the units in Activity mode', () => {
    expect(renderToString(<CalendarLegend mode="activity" maxActivity={20} />)).toContain(
      'fire-active cell-days, Aqua-equivalent',
    )
  })

  it('explains no data, outside the record, provisional and selected, and every verdict icon', () => {
    const out = renderToString(<CalendarLegend mode="pct" maxActivity={20} />)
    for (const label of ['No data', 'Outside the record', 'Provisional (NRT)', 'Selected month']) {
      expect(out).toContain(label)
    }
    for (const v of VERDICTS) expect(out).toContain(VERDICT_PRESENTATION[v].label)
  })

  it('offers % of normal and Activity', () => {
    const out = renderToString(<ValueModeSelector value="pct" onChange={() => {}} />)
    expect(out).toContain('% of normal')
    expect(out).toContain('Activity')
  })
})
