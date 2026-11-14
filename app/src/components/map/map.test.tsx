import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { VERDICTS, parseMapCell } from '../../api/contract.ts'
import type { MapCell } from '../../api/contract.ts'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { CellInfo } from './CellInfo.tsx'
import { LayerSelector } from './LayerSelector.tsx'
import { Legend } from './Legend.tsx'
import { MonthSelector } from './MonthSelector.tsx'
import { countryIso3 } from './countries.ts'
import { formatEstimate, verdictProbability } from './format.ts'
import { NO_DATA_COLOR, cellFillColor, layerValue, sequentialColor, sharedMax } from './scale.ts'

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
    estimate: 12.34,
    ci90_low: 8.1,
    ci90_high: 16.4,
    sd: 2.5,
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
    reason_codes: ['WIDE_INTERVAL'],
    data_level: 'SP',
    method_version: 'synthetic-test',
    ...overrides,
  })
}

describe('colour scale', () => {
  it('shows null as the distinct "no data" colour, never the low end of the ramp', () => {
    expect(sequentialColor(null, 10)).toEqual(NO_DATA_COLOR)
    expect(sequentialColor(0, 10)).not.toEqual(NO_DATA_COLOR)
    expect(sequentialColor(5, 0)).toEqual(NO_DATA_COLOR)
  })

  it('is monotonic at the ends and clamps above the maximum', () => {
    expect(sequentialColor(0, 10)).not.toEqual(sequentialColor(10, 10))
    expect(sequentialColor(99, 10)).toEqual(sequentialColor(10, 10))
  })

  it('uses one shared maximum over raw and harmonized values', () => {
    const cells = [cell({ raw_combined_cell_days: 40, estimate: 12 }), cell({ raw_combined_cell_days: 5, estimate: 55 })]
    expect(sharedMax(cells)).toBe(55)
    const c = cells[0]
    expect(layerValue(c, 'raw')).toBe(40)
    expect(layerValue(c, 'harmonized')).toBe(12)
    expect(cellFillColor(c, 'raw', 55)).toEqual(sequentialColor(40, 55))
    expect(cellFillColor(c, 'harmonized', 55)).toEqual(sequentialColor(12, 55))
  })

  it('shows a null harmonized estimate as no data, not zero', () => {
    const c = cell({ estimate: null, ci90_low: null, ci90_high: null, pct_of_normal: null })
    expect(layerValue(c, 'harmonized')).toBeNull()
    expect(cellFillColor(c, 'harmonized', 50)).toEqual(NO_DATA_COLOR)
  })

  it('gives every verdict its own fill colour in verdict mode', () => {
    const colours = VERDICTS.map((verdict) => JSON.stringify(cellFillColor(cell({ verdict }), 'verdict', 10)))
    expect(new Set(colours).size).toBe(VERDICTS.length)
  })
})

describe('formatting', () => {
  it('writes probabilities as whole percentages', () => {
    expect(verdictProbability(cell())).toBe('82% likely above normal')
  })

  it('gives no probability wording for CANNOT_DETERMINE or NO_DETECTED_ACTIVITY', () => {
    expect(verdictProbability(cell({ verdict: 'CANNOT_DETERMINE' }))).toBeNull()
    expect(verdictProbability(cell({ verdict: 'NO_DETECTED_ACTIVITY' }))).toBeNull()
  })

  it('shows a null estimate as no data', () => {
    expect(formatEstimate(cell({ estimate: null, ci90_low: null, ci90_high: null }))).toBe('no data')
  })
})

describe('countryIso3', () => {
  it('uses ISO_A3_EH, which fixes Norway and France where ISO_A3 is -99', () => {
    expect(countryIso3({ ISO_A3: '-99', ISO_A3_EH: 'NOR' })).toBe('NOR')
  })

  it('returns null, not an invented code, for features without an ISO code', () => {
    expect(countryIso3({ ISO_A3_EH: '-99', ADM0_A3: 'KOS' })).toBeNull()
    expect(countryIso3(undefined)).toBeNull()
  })
})

describe('CellInfo (tooltip)', () => {
  it('shows verdict with icon and text, probability, values, units and reasons', () => {
    const html = renderToString(<CellInfo cell={cell()} />)
    expect(html).toContain('Above normal')
    expect(html).toContain('▲')
    expect(html).toContain('82% likely above normal')
    expect(html).toContain('137% of normal')
    expect(html).toContain('90% interval 8.1 to 16.4')
    expect(html).toContain('fire-active cell-days')
    expect(html).toContain('Wide uncertainty')
  })

  it('shows "no data" for null values and never 0', () => {
    const html = renderToString(<CellInfo cell={cell({ estimate: null, ci90_low: null, ci90_high: null, pct_of_normal: null })} />)
    expect(html).toContain('no data')
    expect(html).not.toContain('0% of normal')
  })

  it('marks provisional data', () => {
    expect(renderToString(<CellInfo cell={cell({ data_level: 'NRT' })} />)).toContain('Provisional')
  })

  it('shows CANNOT_DETERMINE as a result, not an error', () => {
    const html = renderToString(<CellInfo cell={cell({ verdict: 'CANNOT_DETERMINE' })} />)
    expect(html).toContain('Cannot determine')
    expect(html).not.toContain('error')
  })
})

describe('Legend', () => {
  it('lists every verdict with its label in verdict mode', () => {
    const html = renderToString(<Legend layer="verdict" max={0} />)
    for (const label of ['Above normal', 'Below normal', 'Within normal', 'Cannot determine', 'No detected activity']) {
      expect(html).toContain(label)
    }
  })

  it('states the units in raw and harmonized modes', () => {
    for (const layer of ['raw', 'harmonized'] as const) {
      expect(renderToString(<Legend layer={layer} max={50} />)).toContain('Fire-active cell-days, Aqua-equivalent')
    }
  })
})

describe('MonthSelector', () => {
  const months = [
    { year: 2026, month: 9, provisional: false },
    { year: 2026, month: 10, provisional: true },
  ]

  it('shows the month and a provisional badge', () => {
    const html = renderToString(<MonthSelector months={months} value={{ year: 2026, month: 10 }} onChange={() => {}} />)
    expect(html).toContain('October 2026')
    expect(html).toContain('Provisional')
  })

  it('has labelled controls and handles an empty month list', () => {
    const html = renderToString(<MonthSelector months={[]} value={null} onChange={() => {}} />)
    expect(html).toContain('aria-label="Previous month"')
    expect(html).toContain('aria-label="Month slider"')
    expect(html).toContain('No month available')
  })
})

describe('LayerSelector', () => {
  it('offers the three layer modes', () => {
    const html = renderToString(<LayerSelector value="verdict" onChange={() => {}} />)
    expect(html).toContain('Verdict')
    expect(html).toContain('Raw')
    expect(html).toContain('Harmonized')
  })
})

describe('states', () => {
  it('renders loading, error with retry, and empty', () => {
    expect(renderToString(<LoadingState what="map data" />)).toContain('Loading map data')
    const error = renderToString(<ErrorState message="Data are not available right now." onRetry={() => {}} />)
    expect(error).toContain('Data are not available right now.')
    expect(error).toContain('Retry')
    expect(renderToString(<EmptyState message="No cells for this month." />)).toContain('No cells for this month.')
  })
})
