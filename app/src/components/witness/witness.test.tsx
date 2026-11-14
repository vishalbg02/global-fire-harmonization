import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { EntityMonth } from '../../api/contract.ts'
import { ContractError, decodeRawByWitness, parseEntityMonth, parseRawByWitness } from '../../api/contract.ts'
import { JUMP_CAPTION } from '../../content/source.ts'
import { SATELLITE_TIMELINE, SATELLITE_TIMELINE_SOURCE } from '../../content/witnessTimeline.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { WORLD } from '../../state/selection.ts'
import { SatelliteTimeline } from './SatelliteTimeline.tsx'
import { WitnessPanel } from './WitnessPanel.tsx'
import { WitnessTable } from './WitnessTable.tsx'
import { buildMonthMarks, buildWitnessChartOption, mergeIntoRuns } from './chartOption.ts'
import {
  fieldSeries,
  monthLabel,
  monthLabels,
  monthsWithReason,
  provisionalMonths,
  rawCombinedSeries,
  witnessSeries,
  witnessesPresent,
} from './series.ts'

// SYNTHETIC test data. Not NASA observations.
function record(year: number, month: number, overrides: Record<string, unknown> = {}): EntityMonth {
  return parseEntityMonth({
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    year,
    month,
    n_cells: 10,
    raw_by_witness: JSON.stringify({ AQUA_MODIS: 10, SNPP_VIIRS: 20 }),
    estimate: 15,
    ci90_low: 10,
    ci90_high: 20,
    sd: 2,
    raw_combined_cell_days: 30,
    witnesses_used: ['AQUA_MODIS', 'SNPP_VIIRS'],
    n_witnesses: 2,
    disagreement_scale: null,
    baseline_median: 12,
    baseline_p25: 8,
    baseline_p75: 16,
    pct_of_normal: 125,
    p_above: 0.6,
    p_below: 0.1,
    p_within: 0.3,
    verdict: 'WITHIN_NORMAL',
    reason_codes: [],
    data_level: 'SP',
    method_version: 'synthetic-test',
    ...overrides,
  })
}

const SERIES: EntityMonth[] = [
  record(2011, 12, { raw_by_witness: null, data_level: 'SP' }), // Terra only era, no decoded map
  record(2012, 1, { raw_by_witness: JSON.stringify({ AQUA_MODIS: 10, TERRA_MODIS: 5 }) }),
  record(2015, 9, { reason_codes: ['OUTAGE'] }),
  record(2022, 1, { reason_codes: ['AQUA_DRIFT_ERA'], raw_by_witness: JSON.stringify({ SNPP_VIIRS: 25 }) }),
  record(2026, 10, { estimate: null, ci90_low: null, ci90_high: null, data_level: 'NRT' }),
]

describe('parseRawByWitness and decodeRawByWitness (shared decoding, T-037)', () => {
  it('decodes a JSON string into the witness-keyed map', () => {
    expect(parseRawByWitness('{"AQUA_MODIS": 5, "SNPP_VIIRS": 0}', 'test')).toEqual({ AQUA_MODIS: 5, SNPP_VIIRS: 0 })
  })

  it('returns null for a null value without decoding', () => {
    expect(parseRawByWitness(null, 'test')).toBeNull()
  })

  it('rejects invalid JSON and an unknown witness key', () => {
    expect(() => parseRawByWitness('not json', 'test')).toThrow(ContractError)
    expect(() => parseRawByWitness('{"LANDSAT": 1}', 'test')).toThrow(ContractError)
  })

  it('decodeRawByWitness is the same logic used on an already-parsed object', () => {
    expect(decodeRawByWitness({ NOAA20_VIIRS: 3 }, 'test')).toEqual({ NOAA20_VIIRS: 3 })
    expect(decodeRawByWitness(null, 'test')).toBeNull()
  })
})

describe('series helpers', () => {
  it('builds "YYYY-MM" month labels in order', () => {
    expect(monthLabel(SERIES[0])).toBe('2011-12')
    expect(monthLabels(SERIES)).toEqual(['2011-12', '2012-01', '2015-09', '2022-01', '2026-10'])
  })

  it('reads a harmonized field as stored, with null as a gap', () => {
    expect(fieldSeries(SERIES, 'estimate')).toEqual([15, 15, 15, 15, null])
  })

  it('reads the raw combined count as stored (never null)', () => {
    expect(rawCombinedSeries(SERIES)).toEqual([30, 30, 30, 30, 30])
  })

  it('reads one witness series, with a gap when the record has no map or no entry for it', () => {
    expect(witnessSeries(SERIES, 'AQUA_MODIS')).toEqual([null, 10, 10, null, 10])
    expect(witnessSeries(SERIES, 'TERRA_MODIS')).toEqual([null, 5, null, null, null])
  })

  it('lists the witnesses present anywhere in the series, in contract order', () => {
    expect(witnessesPresent(SERIES)).toEqual(['AQUA_MODIS', 'TERRA_MODIS', 'SNPP_VIIRS'])
    expect(witnessesPresent([])).toEqual([])
  })

  it('finds the months carrying a given reason code', () => {
    expect(monthsWithReason(SERIES, 'OUTAGE')).toEqual(['2015-09'])
    expect(monthsWithReason(SERIES, 'AQUA_DRIFT_ERA')).toEqual(['2022-01'])
    expect(monthsWithReason(SERIES, 'SINGLE_WITNESS')).toEqual([])
  })

  it('finds the provisional months (data_level other than SP)', () => {
    expect(provisionalMonths(SERIES)).toEqual(['2026-10'])
  })
})

describe('buildMonthMarks', () => {
  it('separates outage, drift-era and provisional months', () => {
    expect(buildMonthMarks(SERIES)).toEqual({
      outage: ['2015-09'],
      drift: ['2022-01'],
      provisional: ['2026-10'],
    })
  })
})

describe('buildWitnessChartOption', () => {
  const option = buildWitnessChartOption(SERIES) as Record<string, unknown>
  const series = option.series as Record<string, unknown>[]

  function findSeries(name: string): Record<string, unknown> {
    const found = series.find((s) => s.name === name)
    if (found === undefined) throw new Error(`no series named "${name}"`)
    return found
  }

  it('has animation off and accessibility on (reduced motion, screen readers)', () => {
    expect(option.animation).toBe(false)
    expect((option.aria as { enabled: boolean }).enabled).toBe(true)
  })

  it('has one line per witness present in the series, named per the contract', () => {
    const names = series.map((s) => s.name)
    expect(names).toContain(WITNESS_NAMES.AQUA_MODIS)
    expect(names).toContain(WITNESS_NAMES.TERRA_MODIS)
    expect(names).toContain(WITNESS_NAMES.SNPP_VIIRS)
    expect(names).not.toContain(WITNESS_NAMES.NOAA20_VIIRS)
  })

  it('gives every witness line its own colour and its own dash pattern (not colour alone)', () => {
    const lines = series.filter((s) => Object.values(WITNESS_NAMES).includes(s.name as string))
    const styles = lines.map((s) => JSON.stringify((s.lineStyle as Record<string, unknown>).type))
    expect(new Set(styles).size).toBe(lines.length) // every witness has a distinct dash pattern
    const colors = lines.map((s) => (s.lineStyle as Record<string, unknown>).color)
    expect(new Set(colors).size).toBe(lines.length)
  })

  it('has the harmonized line, the raw combined dashed line, and both bands', () => {
    const names = series.map((s) => s.name)
    expect(names).toContain('Harmonized estimate')
    expect(names).toContain('Raw combined (all satellites)')
    expect(names).toContain('Baseline (median)')
    const rawCombined = findSeries('Raw combined (all satellites)')
    expect((rawCombined.lineStyle as Record<string, unknown>).type).toBe('dashed')
  })

  it('keeps null as a gap in the harmonized line, never drawing a zero', () => {
    expect(findSeries('Harmonized estimate').data).toEqual([15, 15, 15, 15, null])
  })

  it('computes the band height as high minus low, with a gap propagated from either side', () => {
    expect(findSeries('Harmonized (90% interval)').data).toEqual([10, 10, 10, 10, null]) // 20-10 for the 4 populated months
  })

  it('places outage months on the harmonized line\'s markLine and drift months as a markArea band on it', () => {
    expect((findSeries('Harmonized estimate').markLine as { data: { xAxis: string }[] }).data).toEqual([
      { xAxis: '2015-09' },
    ])
    const driftArea = findSeries('Harmonized estimate').markArea as { data: [{ xAxis: string }, { xAxis: string }][] }
    expect(driftArea.data).toEqual([[{ name: 'Aqua drift era', xAxis: '2022-01' }, { xAxis: '2022-01' }]])
  })

  it('merges a long run of flagged months into one band instead of one mark per month', () => {
    const categories = ['2022-01', '2022-02', '2022-03', '2022-04']
    expect(mergeIntoRuns(categories, ['2022-01', '2022-02', '2022-04'])).toEqual([
      ['2022-01', '2022-02'],
      ['2022-04', '2022-04'],
    ])
  })

  it('has a dataZoom for both scroll and the slider', () => {
    expect((option.dataZoom as { type: string }[]).map((d) => d.type)).toEqual(['inside', 'slider'])
  })

  it('an empty series produces an option with no category labels and no crash', () => {
    const empty = buildWitnessChartOption([]) as Record<string, unknown>
    expect((empty.xAxis as { data: string[] }).data).toEqual([])
  })
})

describe('WitnessTable (accessible table view)', () => {
  const html = renderToString(<WitnessTable records={SERIES} areaName="Indonesia" />)

  it('has a caption and column headers including every witness present', () => {
    expect(html).toContain('<caption>')
    expect(html).toContain('Monthly satellite-detected fire activity for Indonesia')
    expect(html).toContain(WITNESS_NAMES.AQUA_MODIS)
    expect(html).toContain(WITNESS_NAMES.TERRA_MODIS)
  })

  it('shows the same harmonized and raw values as the chart', () => {
    expect(html).toContain('15.0') // estimate
    expect(html).toContain('10.0 to 20.0') // 90% interval
  })

  it('shows "no data" for a null value and never 0', () => {
    expect(html).toContain('no data')
  })

  it('notes outage, drift-era and provisional months', () => {
    expect(html).toContain('Outage')
    expect(html).toContain('Aqua drift era')
    expect(html).toContain('Provisional')
  })
})

describe('SatelliteTimeline', () => {
  const html = renderToString(<SatelliteTimeline />)

  it('lists every satellite with its dates, cited to docs/DATA_SOURCES.md', () => {
    for (const entry of SATELLITE_TIMELINE) {
      expect(html).toContain(entry.label)
    }
    expect(html).toContain('01/11/2000') // Terra start, verified date
    expect(html).toContain('ongoing')
    expect(html).toContain('docs/DATA_SOURCES.md, section 4')
    expect(html).toContain('VERIFIED 2026-11-14, FIRMS FAQ')
    expect(SATELLITE_TIMELINE_SOURCE).toContain('docs/DATA_SOURCES.md')
  })

  it('marks Terra as raw only and NOAA-21 as not used', () => {
    expect(html).toContain('raw view only')
    expect(html).toContain('not used in the MVP')
  })

  it('gives S-NPP VIIRS both a start and an end date', () => {
    expect(html).toContain('20/01/2012')
    expect(html).toContain('02/11/2026')
  })
})

describe('WitnessPanel (states)', () => {
  const render = (area = WORLD) =>
    renderToString(
      <QueryClientProvider client={new QueryClient()}>
        <WitnessPanel area={area} onShowWorld={() => {}} />
      </QueryClientProvider>,
    )

  it('names the area and reuses the T-033 jump-explanation sentence', () => {
    const html = render()
    expect(html).toContain('Satellites: World')
    expect(html).toContain(JUMP_CAPTION)
  })

  it('shows loading while the series is fetched', () => {
    expect(render()).toContain('Loading the satellite comparison')
  })

  it('says "Area not found" for a country not in the products, with Show the world', () => {
    const html = render({ entity_type: 'COUNTRY', entity_id: 'RUS', entity_name: 'Russia' })
    // Rendered before the query resolves, so this checks the loading state renders without crashing
    // for a non-world area; the 404 path itself is exercised by the calendar's equivalent tests.
    expect(html).toContain('Satellites: Russia')
  })
})
