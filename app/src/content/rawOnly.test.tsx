import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { parseEntityMonth, parseEntityEvidence } from '../api/contract.ts'
import type { EntityMonth } from '../api/contract.ts'
import { ValueModeSelector } from '../components/calendar/ValueModeSelector.tsx'
import { AnomalyPanel } from '../components/anomalies/AnomalyPanel.tsx'
import { rankAnomalies } from '../components/anomalies/rankings.ts'
import { SourceToggle } from '../components/common/SourceToggle.tsx'
import { EvidenceBody } from '../components/evidence/EvidenceBody.tsx'
import { MapModeSelector } from '../components/map/MapModeSelector.tsx'
import { buildWitnessChartOption } from '../components/witness/chartOption.ts'
import { NOT_AVAILABLE_YET, RAW_ONLY_HARMONIZED_UNAVAILABLE, RawOnlyContext, isRawOnly } from './rawOnly.ts'

// SYNTHETIC test data. Not NASA observations. These mirror the raw-only product shape:
// every harmonized field null, verdict CANNOT_DETERMINE, no caveats.
const RAW_ONLY_RECORD = {
  estimate: null,
  ci90_low: null,
  ci90_high: null,
  sd: null,
  raw_combined_cell_days: 6812,
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
  reason_codes: [],
  data_level: 'SP',
  method_version: '0.1.0-raw-only',
}

function evidence() {
  return parseEntityEvidence({
    ...RAW_ONLY_RECORD,
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    year: 2020,
    month: 7,
    n_cells: 10,
    raw_by_witness: { AQUA_MODIS: 431, SNPP_VIIRS: 2990 },
  })
}

function monthRecord(month: number): EntityMonth {
  return parseEntityMonth({
    ...RAW_ONLY_RECORD,
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    year: 2020,
    month,
    n_cells: 10,
    raw_by_witness: JSON.stringify({ AQUA_MODIS: 10, SNPP_VIIRS: 20 }),
  })
}

/** The `<input>` tag of one radio option (attribute order does not matter). */
const input = (html: string, value: string) =>
  new RegExp(`<input[^>]*value="${value}"[^>]*>`).exec(html)?.[0] ?? ''

const rawOnly = (node: React.ReactNode) =>
  renderToString(<RawOnlyContext.Provider value={true}>{node}</RawOnlyContext.Provider>)

describe('isRawOnly', () => {
  it('is true only for a method version ending in -raw-only', () => {
    expect(isRawOnly({ method_version: '0.1.0-raw-only' })).toBe(true)
    expect(isRawOnly({ method_version: '0.1.0' })).toBe(false)
    expect(isRawOnly({ method_version: 'raw-only-0.1' })).toBe(false)
    expect(isRawOnly(null)).toBe(false)
    expect(isRawOnly(undefined)).toBe(false)
  })
})

describe('controls while only raw data exist', () => {
  it('disables Harmonized and writes out why', () => {
    const html = renderToString(
      <SourceToggle value="raw" onChange={() => {}} rawDisabled={false} harmonizedDisabled />,
    )
    expect(html).toContain(RAW_ONLY_HARMONIZED_UNAVAILABLE)
    expect(input(html, 'harmonized')).toContain('aria-disabled="true"')
    expect(input(html, 'raw')).not.toContain('aria-disabled')
  })

  it('leaves Harmonized enabled otherwise', () => {
    const html = renderToString(<SourceToggle value="raw" onChange={() => {}} rawDisabled={false} />)
    expect(html).not.toContain(RAW_ONLY_HARMONIZED_UNAVAILABLE)
    expect(html).not.toContain('aria-disabled')
  })

  it('disables the verdict map mode', () => {
    const html = renderToString(<MapModeSelector value="activity" onChange={() => {}} verdictDisabled />)
    expect(input(html, 'verdict')).toContain('aria-disabled="true"')
    expect(input(html, 'activity')).not.toContain('aria-disabled')
  })

  it('disables the % of normal calendar mode through the context', () => {
    const html = rawOnly(<ValueModeSelector value="activity" onChange={() => {}} />)
    expect(input(html, 'pct')).toContain('aria-disabled="true"')
    expect(html).toContain('% of normal is not available yet')
    expect(renderToString(<ValueModeSelector value="activity" onChange={() => {}} />)).not.toContain('aria-disabled')
  })
})

describe('evidence while only raw data exist', () => {
  it('shows "Not available yet", no verdict, no satellites-used and no caveats, but the raw contributions', () => {
    const html = rawOnly(<EvidenceBody record={evidence()} rawByWitness={evidence().raw_by_witness} contractVersion="0.1.0" />)
    expect(html).toContain('Not available yet')
    expect(html).toContain(NOT_AVAILABLE_YET)
    expect(html).not.toContain('Cannot determine')
    expect(html).not.toContain('Satellites used')
    expect(html).not.toContain('No satellite contributed')
    expect(html).not.toContain('No caveats')
    // The stored reason code is still explained; only the empty "no caveats" message is hidden.
    expect(html).not.toContain('No caveats are recorded')
    expect(html).toContain('Aqua MODIS: 431')
    expect(html).toContain('S-NPP VIIRS: 2990')
    expect(html).toContain('Method version: 0.1.0-raw-only')
  })

  it('shows the NOT_HARMONIZED text under Why when the record carries it (contract 0.1.1)', () => {
    const record = { ...evidence(), reason_codes: ['NOT_HARMONIZED' as const] }
    const html = rawOnly(<EvidenceBody record={record} rawByWitness={record.raw_by_witness} contractVersion="0.1.1" />)
    expect(html).toContain('Why')
    expect(html).toContain("Harmonized values aren&#x27;t computed yet; this shows raw satellite data only.")
    expect(html).toContain('NOT_HARMONIZED')
  })

  it('is unchanged when the products are harmonized', () => {
    const html = renderToString(<EvidenceBody record={evidence()} rawByWitness={evidence().raw_by_witness} contractVersion="0.1.0" />)
    expect(html).toContain('Cannot determine')
    expect(html).toContain('Satellites used')
  })
})

describe('anomaly list while only raw data exist', () => {
  const panel = (value: boolean) =>
    renderToString(
      <RawOnlyContext.Provider value={value}>
        <AnomalyPanel
          month={{ year: 2020, month: 7 }}
          provisional={false}
          status="ready"
          onRetry={() => {}}
          tab="COUNTRY"
          onTabChange={() => {}}
          expanded={false}
          onToggleExpanded={() => {}}
          rankings={rankAnomalies([], 'COUNTRY')}
          totalAreas={226}
          onSelect={() => {}}
        />
      </RawOnlyContext.Provider>,
    )

  it('says not available yet instead of "no areas with a confident verdict"', () => {
    const html = panel(true)
    expect(html).toContain(NOT_AVAILABLE_YET)
    expect(html).not.toContain('No areas with a confident')
  })

  it('keeps the normal empty message for harmonized products', () => {
    expect(panel(false)).toContain('No areas with a confident')
  })
})

describe('witness chart legend', () => {
  it('lists only series that hold stored values', () => {
    const option = buildWitnessChartOption([monthRecord(1), monthRecord(2)]) as {
      legend: { data: string[] }
    }
    const names = option.legend.data
    expect(names).toContain('Raw combined (all satellites)')
    expect(names).toContain('Aqua MODIS')
    expect(names.some((n) => n.startsWith('Harmonized'))).toBe(false)
    expect(names.some((n) => n.startsWith('Baseline'))).toBe(false)
  })
})
