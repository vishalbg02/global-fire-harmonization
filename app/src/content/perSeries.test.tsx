import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { parseEntityEvidence, parseEntityMonth } from '../api/contract.ts'
import type { EntityMonth } from '../api/contract.ts'
import { ValueModeSelector } from '../components/calendar/ValueModeSelector.tsx'
import { EvidenceBody } from '../components/evidence/EvidenceBody.tsx'
import { WitnessPanel } from '../components/witness/WitnessPanel.tsx'
import { customArea } from '../state/bbox.ts'
import type { Area } from '../state/selection.ts'
import { RawOnlyContext, isRawOnlyRecord, isRawOnlySeries } from './rawOnly.ts'

// SYNTHETIC test data. Not NASA observations. A raw-only preset series (every harmonized field
// null) and a harmonized custom-area series (estimate and interval, no baseline) shown together.
const BASE = {
  sd: null,
  raw_combined_cell_days: 500,
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
  data_level: 'SP',
  n_cells: 4,
  year: 2020,
  month: 7,
}
const RAW_ONLY = {
  ...BASE,
  entity_type: 'COUNTRY',
  entity_id: 'IDN',
  entity_name: 'Indonesia',
  estimate: null,
  ci90_low: null,
  ci90_high: null,
  reason_codes: ['NOT_HARMONIZED'],
  method_version: '0.1.0-raw-only',
  raw_by_witness: { AQUA_MODIS: 40 },
}
const HARMONIZED = {
  ...BASE,
  entity_type: 'CUSTOM',
  entity_id: 'CUSTOM',
  entity_name: 'Custom area',
  estimate: 28.8,
  ci90_low: 23.7,
  ci90_high: 34.0,
  witnesses_used: ['AQUA_MODIS', 'SNPP_VIIRS'],
  n_witnesses: 2,
  reason_codes: [],
  method_version: '0.1.0-combined-no-baseline',
  raw_by_witness: { AQUA_MODIS: 40, SNPP_VIIRS: 90 },
}

const month = (raw: object): EntityMonth =>
  parseEntityMonth({ ...raw, raw_by_witness: JSON.stringify((raw as { raw_by_witness: object }).raw_by_witness) })

const INTERVAL = '(90% interval 23.7 to 34.0)'

describe('raw-only is decided per series, not from the global metadata', () => {
  it('knows a raw-only record by its method version or NOT_HARMONIZED', () => {
    expect(isRawOnlyRecord({ method_version: '0.1.0-raw-only', reason_codes: [] })).toBe(true)
    expect(isRawOnlyRecord({ method_version: '0.1.0-combined-no-baseline', reason_codes: ['NOT_HARMONIZED'] })).toBe(true)
    expect(isRawOnlyRecord({ method_version: '0.1.0-combined-no-baseline', reason_codes: [] })).toBe(false)
  })

  it('is raw-only only when the globe is and every record of the series is', () => {
    const rawSeries = [month(RAW_ONLY)]
    const harmonizedSeries = [month(HARMONIZED)]
    expect(isRawOnlySeries(rawSeries, true)).toBe(true)
    expect(isRawOnlySeries(harmonizedSeries, true)).toBe(false)
    expect(isRawOnlySeries([...rawSeries, ...harmonizedSeries], true)).toBe(false)
    expect(isRawOnlySeries(harmonizedSeries, false)).toBe(false)
    expect(isRawOnlySeries(undefined, true)).toBe(true) // not known yet: the global state
    expect(isRawOnlySeries([], true)).toBe(true)
  })

  it('shows a raw-only preset record and a harmonized custom record side by side', () => {
    const html = renderToString(
      <RawOnlyContext.Provider value={true}>
        <div id="preset">
          <EvidenceBody record={parseEntityEvidence(RAW_ONLY)} rawByWitness={{ AQUA_MODIS: 40 }} contractVersion="0.1.1" />
        </div>
        <div id="custom">
          <EvidenceBody record={parseEntityEvidence(HARMONIZED)} rawByWitness={{ AQUA_MODIS: 40, SNPP_VIIRS: 90 }} contractVersion="0.1.1" />
        </div>
      </RawOnlyContext.Provider>,
    )
    const [preset, custom] = html.split('<div id="custom">') as [string, string]
    expect(preset).toContain('Not available yet')
    expect(preset).toContain('Harmonized values aren&#x27;t computed yet')
    expect(preset).not.toContain('Satellites used')
    // The harmonized custom record: estimate and interval shown, no raw-only wording.
    expect(custom).toContain('28.8')
    expect(custom).toContain(INTERVAL)
    expect(custom).toContain('Satellites used')
    expect(custom).not.toContain('Not available yet: raw data only')
  })

  it('shows the satellite chart note for the raw-only preset series only', () => {
    const client = new QueryClient()
    client.setQueryData(['series', 'COUNTRY', 'IDN'], [month(RAW_ONLY)])
    const bbox: [number, number, number, number] = [-58.5, -35, -53, -30]
    const custom: Area = customArea(bbox)
    client.setQueryData(['series-custom', ...bbox], [month(HARMONIZED)])
    const preset: Area = { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' }
    const show = (area: Area) =>
      renderToString(
        <QueryClientProvider client={client}>
          <RawOnlyContext.Provider value={true}>
            <WitnessPanel area={area} onShowWorld={() => {}} />
          </RawOnlyContext.Provider>
        </QueryClientProvider>,
      )
    expect(show(preset)).toContain('are not available yet (raw data only)')
    expect(show(custom)).not.toContain('are not available yet (raw data only)')
  })

  it('words the % of normal note by whether the series is raw-only', () => {
    const raw = renderToString(<ValueModeSelector value="activity" onChange={() => {}} pctUnavailable rawOnly />)
    const noBaseline = renderToString(<ValueModeSelector value="activity" onChange={() => {}} pctUnavailable rawOnly={false} />)
    expect(raw).toContain('(raw data only)')
    expect(noBaseline).toContain('no baseline until the verdicts are computed')
    expect(noBaseline).not.toContain('raw data only')
  })
})
