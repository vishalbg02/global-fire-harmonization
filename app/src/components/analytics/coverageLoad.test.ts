import { readFileSync } from 'node:fs'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetMapColumns } from '../../api/client.ts'
import { decodeMapCells } from '../../api/mapColumns.ts'
import type { CellColumns, EncodedMonth } from '../../api/mapColumns.ts'
import { loadCoverage } from './coverageLoad.ts'

// SYNTHETIC test data (not NASA observations): the SYNTHETIC static sample of tests/test_static_sample.py, with a country and a
// continent assigned to its cells here. The path under test is the one of the real app: the map's cells come from the columnar
// cache (`decodeMapCells`), which carries no country, and the panel gets the areas from the shared cell list.
const SAMPLE = new URL('../../api/__fixtures__/static/', import.meta.url)
const sample = (path: string): unknown => JSON.parse(readFileSync(new URL(path, SAMPLE), 'utf8'))
const cells = sample('cells.json') as CellColumns
const ids = cells.cell_id as string[]
const country = ids.map((_, i) => (i < 60 ? 'IDN' : i < 90 ? 'MYS' : i < 190 ? 'BRA' : null))
const continent = ids.map((_, i) => (i < 90 ? 'AS' : i < 190 ? 'SA' : null))
const WITH_AREAS: CellColumns = { ...cells, country_iso3: country, continent }

const UNREAD = ['sd', 'n_witnesses', 'baseline_median', 'baseline_p25', 'baseline_p75']
const full = sample('map/2026-10.json') as EncodedMonth
const month: EncodedMonth = { n: full.n, columns: Object.fromEntries(Object.entries(full.columns).filter(([k]) => !UNREAD.includes(k))) }
const mapCells = decodeMapCells(month, cells)

function stubCellList(columns: CellColumns) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ n: ids.length, columns }), { status: 200 })))
}

describe('loadCoverage on the cells the app holds (T-090)', () => {
  beforeEach(() => resetMapColumns())
  afterEach(() => {
    vi.unstubAllGlobals()
    resetMapColumns()
  })

  it('the map cell cache carries no country: the panel must get the areas elsewhere (the bug the Lead found in the real app)', () => {
    expect(mapCells.length).toBeGreaterThan(100)
    for (const c of mapCells) {
      expect(c).not.toHaveProperty('country_iso3')
      expect(c).not.toHaveProperty('continent')
    }
  })

  it('counts a country by the areas of the cell list, for cells that came from the cache without them', async () => {
    stubCellList(WITH_AREAS)
    const result = await loadCoverage({ entityType: 'COUNTRY', entityId: 'IDN' }, mapCells)
    const expected = mapCells.filter((c) => country[ids.indexOf(c.cell_id)] === 'IDN')
    expect(result.status).toBe('ready')
    if (result.status === 'ready') {
      expect(result.coverage?.cells).toBe(expected.length)
      expect(result.coverage?.determinable).toBe(expected.filter((c) => c.verdict !== 'CANNOT_DETERMINE').length)
      expect(expected.length).toBeGreaterThan(0)
      expect(expected.length).toBeLessThan(mapCells.length)
    }
  })

  it('counts a continent, and the world counts every cell without asking for areas', async () => {
    stubCellList(WITH_AREAS)
    const asia = await loadCoverage({ entityType: 'CONTINENT', entityId: 'AS' }, mapCells)
    expect(asia.status === 'ready' && asia.coverage?.cells).toBe(mapCells.filter((c) => continent[ids.indexOf(c.cell_id)] === 'AS').length)
    const spy = vi.fn(async () => null)
    const world = await loadCoverage({ entityType: 'GLOBAL', entityId: 'GLOBAL' }, mapCells, spy)
    expect(world.status === 'ready' && world.coverage?.cells).toBe(mapCells.length)
    expect(spy).not.toHaveBeenCalled()
  })

  it('says the areas are missing, with no figure, when the cell list has none (an older API) or there is no cell list (the offline copy)', async () => {
    stubCellList(cells)
    expect(await loadCoverage({ entityType: 'COUNTRY', entityId: 'IDN' }, mapCells)).toEqual({ status: 'areas-missing' })
    expect(await loadCoverage({ entityType: 'COUNTRY', entityId: 'IDN' }, mapCells, async () => null)).toEqual({ status: 'areas-missing' })
  })
})
