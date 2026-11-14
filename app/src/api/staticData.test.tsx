import { readFileSync } from 'node:fs'
import { renderToString } from 'react-dom/server'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { OfflineNote } from '../components/common/OfflineNote.tsx'
import { offlineNoteText } from '../content/offline.ts'
import { CustomAreaForm } from '../components/area/CustomAreaForm.tsx'
import { ApiError, fetchAnomalies, fetchCsv, fetchCustomSeries, fetchEvidence, fetchMapCells, fetchMeta, fetchSeries, fetchValidation } from './client.ts'
import { parseMapCells } from './contract.ts'
import { decodeMonth, enterStaticMode, resetStaticMode, STATIC_CUSTOM_MESSAGE } from './staticData.ts'
import type { CellColumns, EncodedMonth } from './staticData.ts'

// SYNTHETIC test data. The sample files come from the SYNTHETIC fixtures (tests/test_static_sample.py).
const SAMPLE = new URL('./__fixtures__/static/', import.meta.url)
const sample = (path: string): unknown => JSON.parse(readFileSync(new URL(path, SAMPLE), 'utf8'))
const MONTHS = ['2004-07', '2013-07', '2026-09', '2026-10']

describe('the compact map layout decodes to exactly the API response', () => {
  const cells = sample('cells.json') as CellColumns
  for (const label of MONTHS) {
    it(`${label}: the rebuilt records are identical to /api/map, and so are the parsed MapCells`, () => {
      const decoded = decodeMonth(sample(`map/${label}.json`) as EncodedMonth, cells)
      const api = sample(`api-map/${label}.json`)
      expect(decoded).toEqual(api)
      expect(parseMapCells(decoded)).toEqual(parseMapCells(api))
    })
  }

  it('covers an outage month, a witness-disagreement month, a MIXED month and an NRT month', () => {
    const levels = (label: string) =>
      new Set((sample(`api-map/${label}.json`) as { data_level: string }[]).map((r) => r.data_level))
    const codes = (label: string) =>
      new Set((sample(`api-map/${label}.json`) as { reason_codes: string[] }[]).flatMap((r) => r.reason_codes))
    expect(codes('2004-07').has('OUTAGE')).toBe(true)
    expect(codes('2013-07').has('WITNESS_DISAGREEMENT')).toBe(true)
    expect(levels('2026-09').has('MIXED')).toBe(true)
    expect(levels('2026-10').has('NRT')).toBe(true)
  })
})

// A fake static site (and a down or a live API) behind fetch.
const META = {
  contract_version: '0.1.1', method_version: '0.1.0-raw-only', synthetic: true, generated_at: '2026-11-14T00:00:00Z',
  grid: { analysis_deg: 0.5, fine_deg: null }, baseline_years: [], first_month: '2002-07', latest_month: '2026-11',
  provisional_months: ['2026-11'], witnesses: ['AQUA_MODIS'], data_snapshot: { zips_downloaded: '2026-11-14', api_pulled: null },
  citation: 'SYNTHETIC citation.',
}
const MANIFEST = {
  format_version: 1, exported_at: '2026-11-15T10:00:00Z', synthetic: true, contract_version: '0.1.1',
  method_version: '0.1.0-raw-only', data_snapshot: { zips_downloaded: '2026-11-14', api_pulled: null },
  months: MONTHS, exports: { 'COUNTRY-BRA': 'SYNTHETIC_fire_COUNTRY_BRA.csv' },
}
const RECORD = {
  entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil', year: 2020, month: 3, estimate: 10, ci90_low: 8, ci90_high: 12,
  sd: 1, raw_combined_cell_days: 5, witnesses_used: ['AQUA_MODIS'], n_witnesses: 1, disagreement_scale: null, baseline_median: null,
  baseline_p25: null, baseline_p75: null, pct_of_normal: null, p_above: null, p_below: null, p_within: null, verdict: 'CANNOT_DETERMINE',
  reason_codes: [], data_level: 'SP', method_version: '0.1.0-combined-no-baseline', n_cells: 3,
  raw_by_witness: JSON.stringify({ AQUA_MODIS: 5 }),
}
const FILES: Record<string, unknown> = {
  'manifest.json': MANIFEST,
  'validation.json': { contract_version: '0.1.1', method_version: '0.1.0', generated_at: '2026-11-14T00:00:00Z', synthetic: true, tests: [] },
  'meta.json': META,
  'series/COUNTRY-BRA.json': [RECORD],
  'anomalies/2026-10.json': [],
  'cells.json': sample('cells.json'),
  'map/2026-10.json': sample('map/2026-10.json'),
}

function fakeFetch(apiUp: boolean | 'host-404' | 'gateway-502', withCopy = true) {
  return vi.fn(async (input: string | URL | Request) => {
    const url = String(input)
    const json = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
    if (url.includes('/data/')) {
      const path = url.split('/data/')[1] as string
      if (!withCopy) return new Response('<html></html>', { status: 200, headers: { 'Content-Type': 'text/html' } })
      if (path === 'export/COUNTRY-BRA.csv') return new Response('csv', { status: 200 })
      return path in FILES ? json(FILES[path]) : json({}, 404)
    }
    if (apiUp === 'host-404') return new Response('<html>Not found</html>', { status: 404, headers: { 'Content-Type': 'text/html' } })
    if (apiUp === 'gateway-502') return new Response('Bad gateway', { status: 502, headers: { 'Content-Type': 'text/plain' } })
    if (apiUp === false) throw new TypeError('network down')
    if (url.includes('/api/series')) return json({ detail: 'Unknown entity.' }, 404)
    return json(META)
  })
}

describe('the offline copy (T-043)', () => {
  beforeEach(() => resetStaticMode())
  afterEach(() => {
    vi.unstubAllGlobals()
    resetStaticMode()
  })

  it('falls back to the files when the API cannot be reached, for every preset view', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    expect((await fetchMeta()).synthetic).toBe(true)
    const series = await fetchSeries('COUNTRY', 'BRA')
    expect(series).toHaveLength(1)
    const evidence = await fetchEvidence('COUNTRY', 'BRA', 2020, 3)
    expect(evidence.raw_by_witness).toEqual({ AQUA_MODIS: 5 })
    expect(await fetchAnomalies(2026, 10)).toEqual([])
    const cellsOfMonth = await fetchMapCells(2026, 10, 'raw')
    expect(cellsOfMonth).toEqual(parseMapCells(sample('api-map/2026-10.json')))
  })

  it('also falls back when the host answers for the API with an error that is not the API\'s own', async () => {
    // A static host with no /api route (an HTML 404) and a gateway in front of a dead API (a 502).
    for (const mode of ['host-404', 'gateway-502'] as const) {
      resetStaticMode()
      vi.stubGlobal('fetch', fakeFetch(mode))
      expect((await fetchMeta()).synthetic).toBe(true)
    }
  })

  it('serves the validation results from the copy too, as stored (the methods page, T-041)', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    const results = await fetchValidation()
    expect(results.tests).toEqual([])
    expect(results.synthetic).toBe(true)
  })

  it('does not replace an answer of the API (404, 503) with the copy and does not enter offline mode', async () => {
    const fetchMock = fakeFetch(true)
    vi.stubGlobal('fetch', fetchMock)
    await expect(fetchSeries('COUNTRY', 'ZZZ')).rejects.toMatchObject({ status: 404 })
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes('/data/'))).toBe(false)
    const text = renderToString(<OfflineNote manifest={null} />)
    expect(text).toBe('')
  })

  it('keeps the original error when the API is down and there is no copy', async () => {
    vi.stubGlobal('fetch', fakeFetch(false, false))
    await expect(fetchMeta()).rejects.toMatchObject({ status: null })
  })

  it('answers a missing record or file with a 404, like the API', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    await expect(fetchEvidence('COUNTRY', 'BRA', 1999, 1)).rejects.toMatchObject({ status: 404 })
    await expect(fetchSeries('COUNTRY', 'XXX')).rejects.toBeInstanceOf(ApiError)
  })

  it('has no custom areas: the message says so, and the CSV of a drawn box is refused', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    await expect(fetchCustomSeries([0, 0, 1, 1])).rejects.toMatchObject({ status: 503, detail: STATIC_CUSTOM_MESSAGE })
    await expect(
      fetchCsv({ entity_type: 'CUSTOM', entity_id: 'x', bbox: [0, 0, 1, 1] }, true),
    ).rejects.toMatchObject({ status: 503, detail: STATIC_CUSTOM_MESSAGE })
  })

  it('serves the pre-made CSV of a preset area under the file name the real export code gave it', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    const file = await fetchCsv({ entity_type: 'COUNTRY', entity_id: 'BRA' }, true)
    expect(file.filename).toBe('SYNTHETIC_fire_COUNTRY_BRA.csv')
    expect(await file.blob.text()).toBe('csv')
  })

  it('shows a visible notice with the date of the copy and the data snapshot, and disables custom areas', async () => {
    vi.stubGlobal('fetch', fakeFetch(false))
    const manifest = await enterStaticMode()
    const note = renderToString(<OfflineNote manifest={manifest} />)
    expect(note).toContain('Offline copy')
    expect(note).toContain('2026-11-15')
    expect(note).toContain('Data snapshot: 2026-11-14')
    expect(offlineNoteText(manifest)).toContain('Custom areas need the live service')
    const form = renderToString(
      <CustomAreaForm initial={null} onSubmit={() => {}} drawing={false} onToggleDrawing={() => {}} serverMessage={null} loading={false} />,
    )
    expect(form).toContain(STATIC_CUSTOM_MESSAGE)
    expect(/<button[^>]*type="submit"[^>]*disabled/.test(form) || /<button[^>]*disabled[^>]*type="submit"/.test(form)).toBe(true)
  })
})
