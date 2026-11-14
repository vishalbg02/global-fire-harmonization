import { afterEach, describe, expect, it, vi } from 'vitest'
import { ANOMALIES_MAX_LIMIT, ApiError, errorDetail, fetchAnomalies, fetchCustomSeries, fetchEntities, fetchEvidence, fetchSeries } from './client.ts'
import { ContractError } from './contract.ts'

// SYNTHETIC test data. Not NASA observations.
const RECORD = {
  entity_type: 'GLOBAL',
  entity_id: 'GLOBAL',
  entity_name: 'World',
  year: 2020,
  month: 1,
  n_cells: 4,
  raw_by_witness: null,
  estimate: 5,
  ci90_low: 4,
  ci90_high: 6,
  sd: 0.5,
  raw_combined_cell_days: 6,
  witnesses_used: ['SNPP_VIIRS'],
  n_witnesses: 1,
  disagreement_scale: null,
  baseline_median: 5,
  baseline_p25: 3,
  baseline_p75: 7,
  pct_of_normal: 100,
  p_above: 0.1,
  p_below: 0.1,
  p_within: 0.8,
  verdict: 'WITHIN_NORMAL',
  reason_codes: [],
  data_level: 'SP',
  method_version: 'synthetic-test',
}

function stubFetch(response: { ok: boolean; status: number; body?: unknown }) {
  const fn = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: () => Promise.resolve(response.body),
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('fetchSeries', () => {
  it('requests /api/series with the entity type and id and parses the records', async () => {
    const fetchFn = stubFetch({ ok: true, status: 200, body: [RECORD] })
    const records = await fetchSeries('COUNTRY', 'IDN', 'http://api.test')
    expect(fetchFn).toHaveBeenCalledWith('http://api.test/api/series?entity_type=COUNTRY&entity_id=IDN')
    expect(records).toHaveLength(1)
    expect(records[0].verdict).toBe('WITHIN_NORMAL')
  })

  it('reports an unknown entity as an ApiError with status 404', async () => {
    stubFetch({ ok: false, status: 404, body: { detail: 'Unknown entity' } })
    const error = await fetchSeries('COUNTRY', 'ZZZ', '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('reports an unreachable service as an ApiError without a status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
    const error = await fetchSeries('GLOBAL', 'GLOBAL', '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBeNull()
  })

  it('rejects a record that breaks the contract instead of coercing it', async () => {
    stubFetch({ ok: true, status: 200, body: [{ ...RECORD, verdict: 'MAYBE' }] })
    await expect(fetchSeries('GLOBAL', 'GLOBAL', '')).rejects.toBeInstanceOf(ContractError)
  })
})


describe('fetchEvidence', () => {
  it('requests /api/evidence with the entity, year and month and parses the decoded record', async () => {
    const fetchFn = stubFetch({ ok: true, status: 200, body: { ...RECORD, raw_by_witness: { SNPP_VIIRS: 7 } } })
    const evidence = await fetchEvidence('COUNTRY', 'IDN', 2015, 9, 'http://api.test')
    expect(fetchFn).toHaveBeenCalledWith(
      'http://api.test/api/evidence?entity_type=COUNTRY&entity_id=IDN&year=2015&month=9',
    )
    expect(evidence.raw_by_witness).toEqual({ SNPP_VIIRS: 7 })
  })

  it('reports an unknown entity or month as an ApiError with status 404', async () => {
    stubFetch({ ok: false, status: 404, body: { detail: 'Unknown entity' } })
    const error = await fetchEvidence('COUNTRY', 'ZZZ', 2020, 1, '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('reports a service failure as an ApiError and rejects a record that breaks the contract', async () => {
    stubFetch({ ok: false, status: 503, body: { detail: 'down' } })
    const down = await fetchEvidence('GLOBAL', 'GLOBAL', 2020, 1, '').catch((e: unknown) => e)
    expect((down as ApiError).status).toBe(503)
    stubFetch({ ok: true, status: 200, body: { ...RECORD, raw_by_witness: { LANDSAT: 1 } } })
    await expect(fetchEvidence('GLOBAL', 'GLOBAL', 2020, 1, '')).rejects.toBeInstanceOf(ContractError)
  })
})


describe('fetchEntities', () => {
  it('requests the list of one type and parses the boxes', async () => {
    const fetchFn = stubFetch({
      ok: true,
      status: 200,
      body: [{ entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil', bbox: [-56, -12, -53, -9.5] }],
    })
    const items = await fetchEntities('COUNTRY', 'http://api.test')
    expect(fetchFn).toHaveBeenCalledWith('http://api.test/api/entities?type=COUNTRY')
    expect(items[0].bbox).toEqual([-56, -12, -53, -9.5])
  })

  it('rejects a list that breaks the contract', async () => {
    stubFetch({ ok: true, status: 200, body: [{ entity_type: 'COUNTRY' }] })
    await expect(fetchEntities('CONTINENT', '')).rejects.toBeInstanceOf(ContractError)
  })
})

describe('errorDetail', () => {
  it('reads a string detail and a list of messages, and nothing else', () => {
    expect(errorDetail({ detail: 'No analysis cells have their centre inside this area.' })).toBe(
      'No analysis cells have their centre inside this area.',
    )
    expect(errorDetail({ detail: [{ msg: 'a' }, { msg: 'b' }] })).toBe('a; b')
    expect(errorDetail({ detail: '  ' })).toBeNull()
    expect(errorDetail({ detail: [] })).toBeNull()
    expect(errorDetail({ other: 1 })).toBeNull()
    expect(errorDetail(null)).toBeNull()
    expect(errorDetail('text')).toBeNull()
  })
})

describe('fetchCustomSeries', () => {
  const BOX = [100, 0, 101, 1] as const

  it('posts the box as JSON and parses the returned records', async () => {
    const fetchFn = stubFetch({ ok: true, status: 200, body: [{ ...RECORD, entity_type: 'CUSTOM', entity_id: 'custom_x', entity_name: 'Custom area' }] })
    const records = await fetchCustomSeries(BOX, 'http://api.test')
    expect(fetchFn).toHaveBeenCalledTimes(1)
    const [url, init] = fetchFn.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://api.test/api/series/custom')
    expect(init.method).toBe('POST')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body as string)).toEqual({ bbox: [100, 0, 101, 1] })
    expect(records[0].entity_type).toBe('CUSTOM')
  })

  it('carries the server message of a 422 in ApiError.detail', async () => {
    stubFetch({ ok: false, status: 422, body: { detail: 'No analysis cells have their centre inside this area.' } })
    const error = await fetchCustomSeries(BOX, '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(422)
    expect((error as ApiError).detail).toBe('No analysis cells have their centre inside this area.')
  })

  it('carries the server message of a 503 in ApiError.detail', async () => {
    stubFetch({
      ok: false,
      status: 503,
      body: { detail: 'Custom areas are not available yet: the harmonization function has not been delivered.' },
    })
    const error = await fetchCustomSeries(BOX, '').catch((e: unknown) => e)
    expect((error as ApiError).status).toBe(503)
    expect((error as ApiError).detail).toContain('not available yet')
  })

  it('has no detail when the error response has no readable body, and reports an unreachable service', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: () => Promise.reject(new Error('no body')) }))
    const noBody = await fetchCustomSeries(BOX, '').catch((e: unknown) => e)
    expect((noBody as ApiError).detail).toBeNull()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
    const down = await fetchCustomSeries(BOX, '').catch((e: unknown) => e)
    expect((down as ApiError).status).toBeNull()
  })

  it('rejects a record that breaks the contract instead of coercing it', async () => {
    stubFetch({ ok: true, status: 200, body: [{ ...RECORD, verdict: 'MAYBE' }] })
    await expect(fetchCustomSeries(BOX, '')).rejects.toBeInstanceOf(ContractError)
  })
})


describe('fetchAnomalies', () => {
  const item = { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia', verdict: 'ABOVE_NORMAL', p_above: 0.9, p_below: 0, pct_of_normal: 250 }

  it('asks for the month with the API maximum by default and parses the entries in the API order', async () => {
    const fetchFn = stubFetch({ ok: true, status: 200, body: [item, { ...item, entity_id: 'BRA' }] })
    const list = await fetchAnomalies(2015, 9, undefined, 'http://api.test')
    expect(fetchFn).toHaveBeenCalledWith(`http://api.test/api/anomalies?year=2015&month=9&limit=${ANOMALIES_MAX_LIMIT}`)
    expect(list.map((a) => a.entity_id)).toEqual(['IDN', 'BRA'])
  })

  it('passes an explicit limit', async () => {
    const fetchFn = stubFetch({ ok: true, status: 200, body: [] })
    await fetchAnomalies(2020, 1, 5, '')
    expect(fetchFn).toHaveBeenCalledWith('/api/anomalies?year=2020&month=1&limit=5')
  })

  it('reports a 400 and a 503 as an ApiError with that status', async () => {
    stubFetch({ ok: false, status: 400, body: { detail: [{ msg: 'bad month' }] } })
    const bad = await fetchAnomalies(2020, 13, 5, '').catch((e: unknown) => e)
    expect((bad as ApiError).status).toBe(400)
    expect((bad as ApiError).detail).toBe('bad month')
    stubFetch({ ok: false, status: 503, body: { detail: 'down' } })
    const down = await fetchAnomalies(2020, 1, 5, '').catch((e: unknown) => e)
    expect((down as ApiError).status).toBe(503)
  })

  it('reports an unreachable service and rejects a verdict the API should never send', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
    const unreachable = await fetchAnomalies(2020, 1, 5, '').catch((e: unknown) => e)
    expect((unreachable as ApiError).status).toBeNull()
    stubFetch({ ok: true, status: 200, body: [{ ...item, verdict: 'CANNOT_DETERMINE' }] })
    await expect(fetchAnomalies(2020, 1, 5, '')).rejects.toBeInstanceOf(ContractError)
  })
})
