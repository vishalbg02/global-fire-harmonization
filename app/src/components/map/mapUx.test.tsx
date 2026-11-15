import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { parseMapCell } from '../../api/contract.ts'
import type { MapCell } from '../../api/contract.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { Legend } from './Legend.tsx'
import { LOADING_TEXT, MapLegend, MapLoading, PINNED_CLOSE, PinnedCellCard, SCROLL_HINT, SCROLL_HINT_MAC, ScrollHint, TOUCH_HINT } from './mapOverlays.tsx'
import { CELL_STROKE_ALPHA, OUTLINE_MIN_ZOOM, cellStrokeWidth } from './scale.ts'

// SYNTHETIC test data. Not NASA observations.
function cell(overrides: Record<string, unknown> = {}): MapCell {
  return parseMapCell({
    cell_id: 'g050_r0123_c0456',
    lat_min: 3,
    lat_max: 3.5,
    lon_min: 46,
    lon_max: 46.5,
    year: 2015,
    month: 9,
    estimate: null,
    ci90_low: null,
    ci90_high: null,
    sd: null,
    raw_combined_cell_days: 4,
    witnesses_used: [],
    n_witnesses: 0,
    disagreement_scale: null,
    baseline_median: null,
    baseline_p25: null,
    baseline_p75: null,
    pct_of_normal: null,
    p_above: null,
    p_below: null,
    p_within: null,
    verdict: 'CANNOT_DETERMINE',
    reason_codes: ['INSUFFICIENT_BASELINE'],
    data_level: 'SP',
    method_version: 'synthetic-test',
    ...overrides,
  })
}

describe('legend on the map', () => {
  it('has the verdict swatches with their icons and labels, in the overlay form', () => {
    const html = renderToString(<MapLegend layer="verdict" max={0} collapsed={false} />)
    for (const p of Object.values(VERDICT_PRESENTATION)) {
      expect(html).toContain(p.label)
      expect(html).toContain(p.icon)
    }
    expect(html).toContain('legend-overlay')
    expect(html).toContain('Legend on the map')
  })

  it('has the activity ramp and the "No data (dark outline)" swatch on the activity layers', () => {
    for (const layer of ['raw', 'harmonized'] as const) {
      const html = renderToString(<MapLegend layer={layer} max={120} collapsed={false} />)
      expect(html).toContain('class="ramp"')
      expect(html).toContain('No data (dark outline)')
      expect(html).toContain('swatch-marked')
    }
  })

  it('can be collapsed: the toggle says so and the body is hidden', () => {
    const html = renderToString(<MapLegend layer="verdict" max={0} collapsed={true} />)
    expect(html).toContain('aria-expanded="false"')
    expect(html).toContain('Show legend')
    expect(html).toMatch(/id="map-legend-body"[^>]*hidden/)
    const open = renderToString(<MapLegend layer="verdict" max={0} collapsed={false} />)
    expect(open).toContain('aria-expanded="true"')
    expect(open).not.toMatch(/id="map-legend-body"[^>]*hidden/)
  })

  it('the sidebar form keeps its long note', () => {
    expect(renderToString(<Legend layer="verdict" max={0} />)).toContain('Each verdict is also given as an icon')
  })
})

describe('pinned cell card', () => {
  it('shows the cell, and the full approved reason sentence for each reason', () => {
    const html = renderToString(<PinnedCellCard cell={cell({ reason_codes: ['INSUFFICIENT_BASELINE', 'WIDE_INTERVAL'] })} layer="verdict" onClose={() => {}} />)
    expect(html).toContain('g050_r0123_c0456')
    expect(html).toContain('There is too little historical fire activity here to define what is normal.')
    expect(html).toContain(REASON_TEXTS.WIDE_INTERVAL.replace(/'/g, '&#x27;'))
    expect(html).toContain(PINNED_CLOSE)
    expect(html).toContain('Esc')
  })

  it('has no reason list when the cell has no reason codes', () => {
    const html = renderToString(<PinnedCellCard cell={cell({ reason_codes: [] })} layer="verdict" onClose={() => {}} />)
    expect(html).not.toContain('cell-reasons')
  })
})

describe('loading indicator and hint', () => {
  it('the loading indicator is announced as a status with its text', () => {
    const html = renderToString(<MapLoading />)
    expect(html).toContain('role="status"')
    expect(html).toContain(LOADING_TEXT)
  })

  // T-091: the old test built a regular expression from SCROLL_HINT, where "+" is an operator (it needed two spaces), so it failed
  // wherever navigator.platform is not a Mac. Plain string checks, on every platform.
  describe.each([
    ['Win32', SCROLL_HINT],
    ['Linux x86_64', SCROLL_HINT],
    ['MacIntel', SCROLL_HINT_MAC],
  ])('the scroll hint on %s', (platform, expected) => {
    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('is on the map, with the touch hint', () => {
      vi.stubGlobal('navigator', { platform })
      const html = renderToString(<ScrollHint />)
      expect(html).toContain(expected)
      expect(html).toContain(expected === SCROLL_HINT ? 'Ctrl' : '⌘')
      expect(html).toContain(TOUCH_HINT)
    })
  })

  it('the old pattern fails on a non-Mac platform (why the test was rewritten)', () => {
    vi.stubGlobal('navigator', { platform: 'Win32' })
    try {
      expect(renderToString(<ScrollHint />)).not.toMatch(new RegExp(`${SCROLL_HINT}|⌘ \+ scroll`))
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

describe('cell outlines (T-071)', () => {
  it('are none at world zoom and grow thin with the zoom, never above 1 px', () => {
    expect(cellStrokeWidth(1.2)).toBe(0)
    expect(cellStrokeWidth(OUTLINE_MIN_ZOOM - 0.01)).toBe(0)
    const widths = [3, 4, 5, 6, 7, 9].map(cellStrokeWidth)
    expect(widths[0]).toBeGreaterThan(0)
    for (let i = 1; i < widths.length; i++) expect(widths[i]).toBeGreaterThanOrEqual(widths[i - 1])
    expect(Math.max(...widths)).toBeLessThanOrEqual(1)
  })

  it('are much lighter than the earlier 1 px [60, 60, 60, 90] stroke', () => {
    expect(CELL_STROKE_ALPHA).toBeLessThan(90 / 2)
  })
})
