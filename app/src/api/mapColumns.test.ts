import { readFileSync } from 'node:fs'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CELL_LIST_TTL_MS, fetchMapCells, MAP_COLUMNS_LAYER, resetMapColumns } from './client.ts'
import { ContractError, parseMapCells } from './contract.ts'
import type { MapCell } from './contract.ts'
import { asCellColumns, asEncodedMonth, decodeMapCells, decodeMonth } from './mapColumns.ts'
import type { CellColumns, EncodedMonth } from './mapColumns.ts'

// SYNTHETIC test data. Not NASA observations. The sample months are the SYNTHETIC fixtures of
// tests/test_static_sample.py: the API's own /api/map answers and their columnar form.
const SAMPLE = new URL('./__fixtures__/static/', import.meta.url)
const sample = (path: string): unknown => JSON.parse(readFileSync(new URL(path, SAMPLE), 'utf8'))
const MONTHS = ['2004-07', '2013-07', '2026-09', '2026-10']
/** The fields GET /api/map/columns does not send (api/fire_api/map_columns.py). */
const UNREAD = ['sd', 'n_witnesses', 'baseline_median', 'baseline_p25', 'baseline_p75']

const cells = sample('cells.json') as CellColumns

/** A month as GET /api/map/columns sends it: the static month without the unread columns. */
function asColumnsResponse(label: string, pick?: number[]): EncodedMonth {
  const full = sample(`map/${label}.json`) as EncodedMonth
  const columns = Object.fromEntries(Object.entries(full.columns).filter(([k]) => !UNREAD.includes(k)))
  if (pick === undefined) return { n: full.n, columns }
  // A month with some of the cells, picked by position in the cell list (what `cell_index` is for).
  const sub: EncodedMonth['columns'] = {}
  for (const [k, c] of Object.entries(columns)) {
    const at = (i: number): unknown =>
      'const' in c ? c.const : 'dict' in c ? c.dict[c.idx[i] as number] : c.values[i]
    sub[k] = { values: pick.map(at) }
  }
  return { n: pick.length, cell_index: pick, columns: sub }
}

const withoutUnread = (cell: MapCell): Record<string, unknown> =>
  Object.fromEntries(Object.entries(cell).filter(([k]) => !UNREAD.includes(k)))

describe('decodeMapCells', () => {
  for (const label of MONTHS) {
    it(`${label}: the same cells as parseMapCells of the API's records, for the fields the map reads`, () => {
      const decoded = decodeMapCells(asColumnsResponse(label), cells)
      const api = parseMapCells(sample(`api-map/${label}.json`))
      expect(decoded).toHaveLength(api.length)
      expect(decoded).toEqual(api.map(withoutUnread))
      // Values are the stored ones, digit for digit.
      expect(JSON.stringify(decoded.map((c) => c.estimate))).toBe(JSON.stringify(api.map((c) => c.estimate)))
    })
  }

  it('does not invent the fields it was not sent', () => {
    const [first] = decodeMapCells(asColumnsResponse('2026-10'), cells)
    for (const key of UNREAD) expect(first).not.toHaveProperty(key)
    expect(first).toHaveProperty('witnesses_used')
    expect(first).toHaveProperty('method_version')
  })

  it('a month with some of the cells decodes to those cells', () => {
    const pick = [5, 17, 198]
    const decoded = decodeMapCells(asColumnsResponse('2013-07', pick), cells)
    const api = parseMapCells(sample('api-map/2013-07.json'))
    expect(decoded.map((c) => c.cell_id)).toEqual(pick.map((i) => (cells.cell_id as string[])[i]))
    expect(decoded).toEqual(pick.map((i) => withoutUnread(api[i] as MapCell)))
  })

  it('decodes const, dict and values columns, nulls and lists', () => {
    const list: CellColumns = {
      cell_id: ['a', 'b', 'c'],
      lat_min: [0, 1, 2],
      lat_max: [1, 2, 3],
      lon_min: [0, 0, 0],
      lon_max: [1, 1, 1],
    }
    const encoded: EncodedMonth = {
      n: 2,
      cell_index: [0, 2],
      columns: {
        year: { const: 2020 },
        reason_codes: { dict: [[], ['OUTAGE']], idx: [1, 0] },
        estimate: { values: [null, 0.30000000000000004] },
      },
    }
    expect(decodeMonth(encoded, list)).toEqual([
      { cell_id: 'a', lat_min: 0, lat_max: 1, lon_min: 0, lon_max: 1, year: 2020, reason_codes: ['OUTAGE'], estimate: null },
      { cell_id: 'c', lat_min: 2, lat_max: 3, lon_min: 0, lon_max: 1, year: 2020, reason_codes: [], estimate: 0.30000000000000004 },
    ])
  })

  it('refuses a month that does not fit the contract or the cell list', () => {
    const month = asColumnsResponse('2026-10')
    const bad = { ...month, columns: { ...month.columns, verdict: { const: 'MAYBE' } } }
    expect(() => decodeMapCells(bad, cells)).toThrow(ContractError)
    expect(() => decodeMapCells({ ...month, cell_index: [999], n: 1, columns: {} }, cells)).toThrow(/out of range/)
    expect(() => asEncodedMonth({ n: 3, columns: { x: { values: [1] } } })).toThrow(/malformed/)
    expect(() => asEncodedMonth({ n: 2, cell_index: [0], columns: {} })).toThrow(/cell_index/)
    expect(() => asEncodedMonth([])).toThrow(ContractError)
    expect(() => asCellColumns({ n: 2, columns: { cell_id: ['a'] } })).toThrow(/malformed/)
  })
})

// ------------------------------------------------------------------ fetchMapCells over the API
function cellsBody(): unknown {
  return { n: (cells.cell_id as unknown[]).length, columns: cells }
}

function stubApi(options: { columns: boolean }) {
  const calls: string[] = []
  const fn = vi.fn(async (input: string | URL | Request) => {
    const url = String(input)
    calls.push(url.replace('http://api.test', ''))
    const json = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
    if (url.includes('/api/map/cells')) return options.columns ? json(cellsBody()) : json({ detail: 'Not Found' }, 404)
    if (url.includes('/api/map/columns')) return options.columns ? json(asColumnsResponse('2026-10')) : json({ detail: 'Not Found' }, 404)
    if (url.includes('/api/map?')) return json(sample('api-map/2026-10.json'))
    return json({ detail: 'Not Found' }, 404)
  })
  vi.stubGlobal('fetch', fn)
  return calls
}

describe('fetchMapCells with the columnar endpoints', () => {
  beforeEach(() => resetMapColumns())
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
    resetMapColumns()
  })

  it('asks for the cell list once and one month of columns, and returns the map cells', async () => {
    const calls = stubApi({ columns: true })
    const first = await fetchMapCells(2026, 10, 'raw', 'http://api.test')
    const second = await fetchMapCells(2026, 9, 'harmonized', 'http://api.test')
    expect(calls.filter((c) => c.startsWith('/api/map/cells'))).toHaveLength(1)
    expect(calls).toContain(`/api/map/columns?year=2026&month=10&layer=${MAP_COLUMNS_LAYER}`)
    expect(calls).toContain(`/api/map/columns?year=2026&month=9&layer=${MAP_COLUMNS_LAYER}`)
    expect(calls.some((c) => c.startsWith('/api/map?'))).toBe(false)
    expect(first).toEqual(parseMapCells(sample('api-map/2026-10.json')).map(withoutUnread))
    expect(second).toHaveLength(first.length)
  })

  it('fetches the cell list again after it has been kept for too long', async () => {
    vi.useFakeTimers()
    const calls = stubApi({ columns: true })
    await fetchMapCells(2026, 10, 'raw', 'http://api.test')
    vi.setSystemTime(Date.now() + CELL_LIST_TTL_MS + 1)
    await fetchMapCells(2026, 10, 'raw', 'http://api.test')
    expect(calls.filter((c) => c.startsWith('/api/map/cells'))).toHaveLength(2)
  })

  it('falls back to /api/map when the API has no columnar endpoint (404), and remembers it', async () => {
    const calls = stubApi({ columns: false })
    const got = await fetchMapCells(2026, 10, 'raw', 'http://api.test')
    expect(got).toEqual(parseMapCells(sample('api-map/2026-10.json')))
    expect(got[0]).toHaveProperty('sd') // the whole record, as before
    expect(calls).toContain('/api/map?year=2026&month=10&layer=raw')
    const before = calls.length
    await fetchMapCells(2026, 10, 'raw', 'http://api.test')
    expect(calls.slice(before)).toEqual(['/api/map?year=2026&month=10&layer=raw'])
  })

  it('does not fall back on an error that is an answer (503) and does not keep a failed cell list', async () => {
    let up = false
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input)
        const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })
        if (!up) return json({ detail: 'Data are not available right now.' }, 503)
        return url.includes('/cells') ? json(cellsBody()) : json(asColumnsResponse('2026-10'))
      }),
    )
    await expect(fetchMapCells(2026, 10, 'raw', 'http://api.test')).rejects.toMatchObject({ status: 503 })
    up = true
    await expect(fetchMapCells(2026, 10, 'raw', 'http://api.test')).resolves.toHaveLength(199)
  })
})
