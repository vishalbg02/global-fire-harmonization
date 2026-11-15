import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchCellAreas, resetMapColumns } from './client.ts'
import { ContractError } from './contract.ts'
import { asCellAreas } from './mapColumns.ts'

// SYNTHETIC test data (not NASA observations): a four-cell list in the layout of GET /api/map/cells.
const BASE = {
  cell_id: ['c1', 'c2', 'c3', 'c4'],
  lat_min: [0, 0.5, -10, 20],
  lat_max: [0.5, 1, -9.5, 20.5],
  lon_min: [100, 100, -50, 10],
  lon_max: [100.5, 100.5, -49.5, 10.5],
}
const WITH_AREAS = { ...BASE, country_iso3: ['IDN', 'IDN', 'BRA', null], continent: ['AS', 'AS', 'SA', null] }

describe('asCellAreas (T-090)', () => {
  it('reads the stored country and continent of every cell, null included', () => {
    expect(asCellAreas(WITH_AREAS)).toEqual({
      cell_id: BASE.cell_id,
      country_iso3: ['IDN', 'IDN', 'BRA', null],
      continent: ['AS', 'AS', 'SA', null],
    })
  })

  it('is null for an API that does not send the two columns, never an invented value', () => {
    expect(asCellAreas(BASE)).toBeNull()
    expect(asCellAreas({ ...BASE, country_iso3: ['IDN', 'IDN', 'BRA', null] })).toBeNull()
  })

  it('rejects malformed columns', () => {
    expect(() => asCellAreas({ ...WITH_AREAS, continent: ['AS'] })).toThrow(ContractError)
    expect(() => asCellAreas({ ...WITH_AREAS, country_iso3: [1, 2, 3, 4] })).toThrow(ContractError)
  })
})

function stub(body: unknown, status = 200) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL | Request) => {
      calls.push(String(input))
      return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
    }),
  )
  return calls
}

describe('fetchCellAreas (T-090)', () => {
  beforeEach(() => resetMapColumns())
  afterEach(() => {
    vi.unstubAllGlobals()
    resetMapColumns()
  })

  it('takes the areas from the shared cell list, fetched once for the session', async () => {
    const calls = stub({ n: 4, columns: WITH_AREAS })
    const first = await fetchCellAreas('http://api.test')
    const second = await fetchCellAreas('http://api.test')
    expect(first?.country_iso3).toEqual(['IDN', 'IDN', 'BRA', null])
    expect(second).toEqual(first)
    expect(calls).toEqual(['http://api.test/api/map/cells'])
  })

  it('is null for an older API (no area columns) and for an API without the endpoint (404)', async () => {
    stub({ n: 4, columns: BASE })
    expect(await fetchCellAreas('http://api.test')).toBeNull()
    resetMapColumns()
    stub({ detail: 'Not Found' }, 404)
    expect(await fetchCellAreas('http://api.test')).toBeNull()
  })

  it('asks the server once, bypassing a kept copy, when the list it has lacks the area columns (a stale HTTP cache), and keeps the fresh list', async () => {
    const inits: (RequestInit | undefined)[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
        inits.push(init)
        const body = init?.cache === 'no-cache' ? { n: 4, columns: WITH_AREAS } : { n: 4, columns: BASE }
        return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }),
    )
    const areas = await fetchCellAreas('http://api.test')
    expect(areas?.country_iso3).toEqual(['IDN', 'IDN', 'BRA', null])
    expect(inits).toHaveLength(2)
    expect(inits[1]).toEqual({ cache: 'no-cache' })
    await fetchCellAreas('http://api.test') // the fresh list is the kept one: no third request
    expect(inits).toHaveLength(2)
  })

  it('still gives null, after one extra request, for an API that really does not send the columns', async () => {
    const calls = stub({ n: 4, columns: BASE })
    expect(await fetchCellAreas('http://api.test')).toBeNull()
    expect(calls).toHaveLength(2)
  })

  it('does not hide an answer that is an error (503)', async () => {
    stub({ detail: 'Data are not available right now.' }, 503)
    await expect(fetchCellAreas('http://api.test')).rejects.toMatchObject({ status: 503 })
  })
})
