import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRef } from 'react'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { REASON_CODES, VERDICTS, parseEntityEvidence, parseMapCell } from '../../api/contract.ts'
import type { EntityEvidence, MapCell } from '../../api/contract.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import type { Area } from '../../state/selection.ts'
import { WORLD } from '../../state/selection.ts'
import { DISAGREEMENT_NOTE, EvidenceBody, PROVISIONAL_NOTICE } from './EvidenceBody.tsx'
import { AreaNotFound, CELL_HEADING, EvidencePanel } from './EvidencePanel.tsx'

// SYNTHETIC test data. Not NASA observations.
const HARMONIZED = {
  estimate: 12.34,
  ci90_low: 8.1,
  ci90_high: 16.4,
  sd: 2,
  raw_combined_cell_days: 20,
  witnesses_used: ['SNPP_VIIRS', 'NOAA20_VIIRS'],
  n_witnesses: 2,
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
}

function evidence(overrides: Record<string, unknown> = {}): EntityEvidence {
  return parseEntityEvidence({
    ...HARMONIZED,
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    year: 2015,
    month: 9,
    n_cells: 10,
    raw_by_witness: { SNPP_VIIRS: 1500, NOAA20_VIIRS: 0, TERRA_MODIS: 77 },
    ...overrides,
  })
}

function mapCell(overrides: Record<string, unknown> = {}): MapCell {
  return parseMapCell({
    ...HARMONIZED,
    cell_id: 'g050_r0123_c0456',
    lat_min: 3,
    lat_max: 3.5,
    lon_min: 46,
    lon_max: 46.5,
    year: 2015,
    month: 9,
    ...overrides,
  })
}

const body = (record: EntityEvidence, contractVersion: string | null = '0.1.0') =>
  renderToString(<EvidenceBody record={record} rawByWitness={record.raw_by_witness} contractVersion={contractVersion} />)

describe('EvidenceBody: the seven items', () => {
  it('1. shows the verdict with icon and label and its probability in whole percentages', () => {
    const html = body(evidence())
    expect(html).toContain('▲')
    expect(html).toContain('Above normal')
    expect(html).toContain('82% likely above normal')
  })

  it('2. shows % of normal as stored and the estimate with its 90% interval and units', () => {
    const html = body(evidence())
    expect(html).toContain('137% of normal')
    expect(html).toContain('12.3 (90% interval 8.1 to 16.4)')
    expect(html).toContain('fire-active cell-days, Aqua-equivalent')
  })

  it('2. computes no interval for the percentage', () => {
    const html = body(evidence())
    expect(html).not.toMatch(/137% of normal \(/)
    expect(html.match(/90% interval/g)).toHaveLength(1)
  })

  it('3. names the witnesses used', () => {
    const html = body(evidence())
    expect(html).toContain('S-NPP VIIRS')
    expect(html).toContain('NOAA-20 VIIRS')
  })

  it('3. says so only when the satellites disagree (scale above 1)', () => {
    expect(body(evidence({ disagreement_scale: 1.4 }))).toContain(`${DISAGREEMENT_NOTE} (disagreement scale 1.40).`)
    expect(body(evidence({ disagreement_scale: 1 }))).not.toContain(DISAGREEMENT_NOTE)
    expect(body(evidence({ disagreement_scale: null }))).not.toContain(DISAGREEMENT_NOTE)
  })

  it('4. shows the raw contribution of each witness, keeps a real zero, and says it is not harmonized', () => {
    const html = body(evidence())
    expect(html).toContain('S-NPP VIIRS: 1500')
    expect(html).toContain('NOAA-20 VIIRS: 0')
    expect(html).toContain('Terra MODIS (raw only): 77')
    expect(html).toContain('not harmonized')
  })

  it('4. shows "no data" when the record has no raw_by_witness, and hides the section for a cell', () => {
    expect(body(evidence({ raw_by_witness: null }))).toContain('no data')
    const cell = renderToString(<EvidenceBody record={mapCell()} contractVersion="0.1.0" />)
    expect(cell).not.toContain('Raw contribution of each satellite')
  })

  it('5. shows every reason code as plain language, with the code as small secondary text', () => {
    const html = body(evidence({ reason_codes: [...REASON_CODES] }))
    for (const code of REASON_CODES) {
      expect(html).toContain(REASON_TEXTS[code].replaceAll("'", '&#x27;'))
      expect(html).toContain(`<small class="reason-code">${code}</small>`)
    }
  })

  it('5. says plainly when there are no caveats', () => {
    expect(body(evidence())).toContain('No caveats are recorded for this month.')
  })

  it('6. shows the provisional notice for NRT and MIXED, and not for SP', () => {
    expect(body(evidence({ data_level: 'NRT' }))).toContain(PROVISIONAL_NOTICE)
    expect(body(evidence({ data_level: 'MIXED' }))).toContain(PROVISIONAL_NOTICE)
    expect(body(evidence({ data_level: 'SP' }))).not.toContain(PROVISIONAL_NOTICE)
  })

  it('7. shows the method version and, from the metadata, the contract version', () => {
    const html = body(evidence())
    expect(html).toContain('Method version: synthetic-test')
    expect(html).toContain('Contract version: 0.1.0')
    expect(body(evidence(), null)).not.toContain('Contract version')
  })

  it('7. has no links yet (the methods page is T-041)', () => {
    expect(body(evidence({ reason_codes: [...REASON_CODES] }))).not.toContain('<a ')
  })
})

describe('EvidenceBody: verdicts and missing values', () => {
  it('shows CANNOT_DETERMINE as a result with its reasons, with no probability and no error styling', () => {
    const html = body(
      evidence({
        verdict: 'CANNOT_DETERMINE',
        p_above: null,
        p_below: null,
        p_within: null,
        reason_codes: ['WIDE_INTERVAL', 'OUTAGE'],
      }),
    )
    expect(html).toContain('Cannot determine')
    expect(html).toContain('This is a result, not an error.')
    expect(html).toContain(REASON_TEXTS.WIDE_INTERVAL)
    expect(html).not.toContain('likely')
    expect(html).not.toContain('role="alert"')
  })

  it('says "No satellite-detected fire activity" for NO_DETECTED_ACTIVITY and never "below normal"', () => {
    const html = body(
      evidence({ verdict: 'NO_DETECTED_ACTIVITY', pct_of_normal: null, p_above: null, p_below: null, p_within: null }),
    )
    expect(html).toContain('No satellite-detected fire activity, and little expected here.')
    expect(html.toLowerCase()).not.toContain('below normal')
  })

  it('shows null values as "no data", never as zero', () => {
    const html = body(evidence({ estimate: null, ci90_low: null, ci90_high: null, pct_of_normal: null }))
    expect(html.match(/no data/g)?.length).toBeGreaterThanOrEqual(2)
    expect(html).not.toContain('0% of normal')
  })

  it('has an icon and a label for every verdict', () => {
    for (const verdict of VERDICTS) {
      const html = body(evidence({ verdict }))
      expect(html).toContain(`aria-hidden="true">${VERDICT_PRESENTATION[verdict].icon} </span>`)
      expect(html).toContain(VERDICT_PRESENTATION[verdict].label)
    }
  })

  it('says so when no satellite contributed', () => {
    expect(body(evidence({ witnesses_used: [], n_witnesses: 0 }))).toContain('No satellite contributed usable data.')
  })
})

describe('EvidencePanel', () => {
  const render = (props: Partial<Parameters<typeof EvidencePanel>[0]> = {}) =>
    renderToString(
      <QueryClientProvider client={new QueryClient()}>
        <EvidencePanel
          area={WORLD}
          month={{ year: 2015, month: 9 }}
          cell={null}
          meta={null}
          headingRef={createRef<HTMLHeadingElement>()}
          onShowWorld={() => {}}
          {...props}
        />
      </QueryClientProvider>,
    )

  it('has a heading that can take focus, naming the area and the month', () => {
    const html = render()
    expect(html).toContain('tabindex="-1"')
    expect(html).toContain('Evidence: World, September 2015')
  })

  it('asks for a month when none is selected', () => {
    expect(render({ month: null })).toContain('Choose a month to see the evidence.')
  })

  it('shows loading while the evidence is fetched', () => {
    expect(render()).toContain('Loading the evidence')
  })

  it('shows a selected cell under the "Cell (no per-satellite breakdown)" heading, with its map record', () => {
    const html = render({ cell: { id: 'g050_r0123_c0456', record: mapCell({ reason_codes: ['OUTAGE'] }), loading: false } })
    expect(html).toContain(CELL_HEADING)
    expect(html).toContain('g050_r0123_c0456, September 2015')
    expect(html).toContain('82% likely above normal')
    expect(html).toContain(REASON_TEXTS.OUTAGE.replace("'", '&#x27;'))
    expect(html).not.toContain('Raw contribution of each satellite')
    expect(html).not.toContain('Loading the evidence')
  })

  it('shows loading and an empty message for a cell that is loading or has no record', () => {
    expect(render({ cell: { id: 'c1', record: null, loading: true } })).toContain('Loading the cell')
    expect(render({ cell: { id: 'c1', record: null, loading: false } })).toContain(
      'This cell has no record for this month.',
    )
  })
})

describe('AreaNotFound', () => {
  const country: Area = { entity_type: 'COUNTRY', entity_id: 'RUS', entity_name: 'Russia' }

  it('says the area was not found and offers "Show the world"', () => {
    const html = renderToString(<AreaNotFound area={country} month={{ year: 2015, month: 9 }} onShowWorld={() => {}} />)
    expect(html).toContain('Area not found: Russia')
    expect(html).toContain('September 2015')
    expect(html).toContain('Show the world')
    expect(html).toContain('role="alert"')
  })

  it('offers no button when the world itself has no record', () => {
    const html = renderToString(<AreaNotFound area={WORLD} month={{ year: 2015, month: 9 }} onShowWorld={() => {}} />)
    expect(html).not.toContain('Show the world')
  })
})
