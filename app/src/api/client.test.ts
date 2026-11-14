import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchSeries } from './client.ts'
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
