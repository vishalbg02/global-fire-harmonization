import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchCsv, fetchCustomSeries } from '../api/client.ts'
import { CustomAreaForm } from '../components/area/CustomAreaForm.tsx'
import type { PolygonControls } from '../components/area/CustomAreaForm.tsx'
import {
  MAX_POLYGON_POINTS,
  POLYGON_MESSAGES,
  checkRing,
  openRing,
  parsePolygonText,
  polygonAnnouncement,
  polygonArea,
  polygonId,
  ringFromLinkText,
  ringToLinkText,
} from './polygon.ts'
import { initialSelection } from './selection.ts'
import type { Selection } from './selection.ts'
import { encodeSelection, selectionFromUrl } from './urlState.ts'

// SYNTHETIC test data. Not NASA observations.
const SQUARE: [number, number][] = [
  [100, 0],
  [101, 0],
  [101, 1],
  [100, 1],
]

afterEach(() => vi.unstubAllGlobals())

describe('parsePolygonText', () => {
  it('reads one longitude, latitude per line, with commas and/or spaces, and ignores blank lines', () => {
    const check = parsePolygonText('100, 0\n\n101 0\r\n  101,1  \n100\t1\n')
    expect(check).toEqual({ ok: true, ring: SQUARE })
  })

  it('accepts a decimal point, a sign and an exponent', () => {
    const check = parsePolygonText('-100.5, 0.25\n-99.5, 0.25\n-1e2, 1')
    expect(check.ok).toBe(true)
  })

  it('rounds to 4 decimals before checking', () => {
    const check = parsePolygonText('100.123456, 0\n101, 0\n101, 1')
    expect(check.ok && check.ring[0]).toEqual([100.1235, 0])
  })

  it.each([
    ['100'],
    ['100, 0, 5'],
    ['abc, 1'],
    ['1,2\n3;4\n5,6'],
    ['NaN, 1\n2, 3\n4, 5'],
  ])('names the line of a malformed row: %j', (text) => {
    const check = parsePolygonText(text)
    expect(check.ok).toBe(false)
    if (!check.ok) expect(check.message).toMatch(/^Line \d+: enter a longitude and a latitude/)
  })

  it('says which line is wrong', () => {
    const check = parsePolygonText('1, 2\n\nx, y')
    expect(!check.ok && check.message.startsWith('Line 3:')).toBe(true)
  })

  it('asks for points when the box is empty', () => {
    const check = parsePolygonText('  \n \n')
    expect(!check.ok && check.message).toContain('Enter the corner points')
  })
})

describe('checkRing: the same rules and messages as the API', () => {
  const message = (points: number[][]) => {
    const check = checkRing(points)
    return check.ok ? null : check.message
  }

  it('accepts a simple and a concave ring', () => {
    expect(checkRing(SQUARE).ok).toBe(true)
    expect(checkRing([[0, 0], [4, 0], [4, 4], [2, 1], [0, 4]]).ok).toBe(true)
  })

  it('accepts exactly 100 points and rejects 101', () => {
    const circle = (n: number) =>
      Array.from({ length: n }, (_, i) => [
        Math.round(10 * Math.cos((2 * Math.PI * i) / n) * 1e4) / 1e4,
        Math.round(10 * Math.sin((2 * Math.PI * i) / n) * 1e4) / 1e4,
      ])
    expect(checkRing(circle(MAX_POLYGON_POINTS)).ok).toBe(true)
    expect(message(circle(MAX_POLYGON_POINTS + 1))).toContain('at most 100 corner points')
  })

  it.each<[string, number[][], string]>([
    ['fewer than 3 different points', [[0, 0], [1, 1], [0, 0]], POLYGON_MESSAGES.notEnough],
    ['two points', [[0, 0], [1, 1]], POLYGON_MESSAGES.notEnough],
    ['a repeated closing point', [[0, 0], [2, 0], [2, 2], [0, 0]], POLYGON_MESSAGES.repeated],
    ['longitude out of range', [[0, 0], [2, 0], [181, 1]], POLYGON_MESSAGES.outOfRange],
    ['latitude out of range', [[0, 0], [2, 0], [1, -91]], POLYGON_MESSAGES.outOfRange],
    ['NaN', [[0, 0], [2, 0], [Number.NaN, 1]], POLYGON_MESSAGES.notFinite],
    ['infinity', [[0, 0], [2, 0], [Number.POSITIVE_INFINITY, 1]], POLYGON_MESSAGES.notFinite],
    ['points on one line', [[0, 0], [1, 1], [2, 2]], POLYGON_MESSAGES.noArea],
    ['the antimeridian', [[170, 0], [-170, 0], [-170, 10], [170, 10]], POLYGON_MESSAGES.antimeridian],
    ['a bow tie', [[0, 0], [2, 2], [2, 0], [0, 2]], POLYGON_MESSAGES.selfIntersecting],
    ['a ring touching itself', [[0, 0], [4, 0], [4, 2], [2, 0], [2, 2], [0, 2]], POLYGON_MESSAGES.selfIntersecting],
    ['a side folded back over another', [[0, 0], [4, 0], [2, 0], [2, 3]], POLYGON_MESSAGES.selfIntersecting],
  ])('rejects %s', (_name, points, expected) => {
    expect(message(points)).toBe(expected)
  })

  it('removes the closing point of a drawn ring', () => {
    expect(openRing([...SQUARE, [100, 0]])).toEqual(SQUARE)
    expect(openRing(SQUARE)).toEqual(SQUARE)
  })
})

describe('the polygon in the page link', () => {
  it('writes POLY:lon,lat;lon,lat with 4 decimals', () => {
    const area = polygonArea([[100.123456, 0], [101, 0], [101, 1.5]])
    const query = encodeSelection({ ...initialSelection, area, month: null })
    expect(new URLSearchParams(query).get('area')).toBe('POLY:100.1235,0;101,0;101,1.5')
  })

  it('round-trips a polygon through the link', () => {
    const area = polygonArea([[100.5, 0.25], [101.75, 0.25], [101, 1.5], [100.5, 1]])
    const selection: Selection = { ...initialSelection, area, entity: area }
    const back = selectionFromUrl(`?${encodeSelection({ ...selection, month: null })}`)
    expect(back.area).toEqual(area)
    expect(back.entity).toEqual(area)
    expect(back.area.entity_type === 'CUSTOM' && back.area.bbox).toEqual([100.5, 0.25, 101.75, 1.5])
  })

  it('ignores a malformed, over-limit or invalid link instead of failing', () => {
    const over = Array.from({ length: 101 }, (_, i) => `${i / 100},${(i % 2) / 100}`).join(';')
    for (const text of [
      'POLY:',
      'POLY:1,2;3,4',
      'POLY:a,b;c,d;e,f',
      'POLY:1,2,3;4,5,6;7,8,9',
      'POLY:0,0;2,2;2,0;0,2', // bow tie
      'POLY:0,0;1,0;200,5', // out of range
      `POLY:${over}`,
    ]) {
      const selection = selectionFromUrl(`?area=${encodeURIComponent(text)}&month=2020-01`)
      expect(selection.area.entity_type).toBe('GLOBAL')
      expect(selection.month).toEqual({ year: 2020, month: 1 })
    }
  })

  it('gives two different polygons different ids and the same polygon the same id', () => {
    expect(polygonId(SQUARE)).toBe(polygonId(SQUARE.map((p) => [...p] as [number, number])))
    expect(polygonId(SQUARE)).not.toBe(polygonId([[100, 0], [101, 0], [101, 2], [100, 2]]))
    expect(polygonId(SQUARE)).not.toBe(polygonArea([[0, 0], [1, 0], [0, 1]]).entity_id)
  })

  it('reads a ring from link text', () => {
    expect(ringFromLinkText(ringToLinkText(SQUARE))).toEqual(SQUARE)
  })
})

describe('the polygon form', () => {
  const polygon = (overrides: Partial<PolygonControls> = {}): PolygonControls => ({
    onSubmit: () => {},
    drawing: false,
    onToggleDrawing: () => {},
    cells: null,
    ...overrides,
  })
  const form = (p: PolygonControls | undefined) =>
    renderToString(
      <CustomAreaForm
        initial={null}
        polygon={p}
        onSubmit={() => {}}
        drawing={false}
        onToggleDrawing={() => {}}
        serverMessage={null}
        loading={false}
      />,
    )

  it('is absent without polygon controls', () => {
    expect(form(undefined)).not.toContain('Draw a polygon on the map')
  })

  it('has a labelled text box, the two buttons, the rule and its consequences', () => {
    const html = form(polygon())
    expect(html).toContain('<textarea')
    expect(html).toContain('Corner points, one per line: longitude, latitude (degrees)')
    expect(html).toContain('Show polygon')
    expect(html).toContain('Draw a polygon on the map')
    expect(html).toContain('centre lies inside it')
    expect(html).toContain('60%')
    expect(html).toContain('may contain no cell centre')
    expect(html).toContain('100 corner points')
  })

  it('explains how to finish and cancel while drawing', () => {
    const html = form(polygon({ drawing: true }))
    expect(html).toContain('Cancel drawing')
    expect(html).toContain('double-click or the Enter key')
    expect(html).toContain('Escape')
  })

  it('fills the text box with a drawn or current polygon', () => {
    const html = form(polygon({ initial: SQUARE }))
    expect(html).toContain('100, 0\n101, 0\n101, 1\n100, 1')
  })

  it('announces the polygon with its corner points and grid cells', () => {
    const html = form(polygon({ initial: SQUARE, active: true, cells: 7 }))
    expect(html).toMatch(/role="status"[^>]*>Custom polygon, 4 corner points, 7 grid cells</)
    expect(polygonAnnouncement(4, 7)).toBe('Custom polygon, 4 corner points, 7 grid cells')
    expect(polygonAnnouncement(4, null)).toBe('Custom polygon, 4 corner points')
    expect(form(polygon({ initial: SQUARE, active: false, cells: 7 }))).not.toContain('Custom polygon, 4')
  })

  it('shows why a drawn polygon was not accepted', () => {
    const html = form(polygon({ initial: SQUARE, drawError: POLYGON_MESSAGES.selfIntersecting }))
    expect(html).toContain('role="alert"')
    expect(html).toContain('crosses or touches itself')
  })
})

describe('requests', () => {
  it('posts a polygon as {"polygon": [...]} to the series endpoint', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve([]) })
    vi.stubGlobal('fetch', fetchFn)
    await fetchCustomSeries({ polygon: SQUARE }, 'http://api.test')
    const [url, init] = fetchFn.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://api.test/api/series/custom')
    expect(JSON.parse(init.body as string)).toEqual({ polygon: SQUARE })
  })

  it('exports a polygon with POST and the same body', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response('a', { headers: { 'Content-Disposition': 'attachment; filename="SYNTHETIC_x.csv"' } }),
    )
    vi.stubGlobal('fetch', fetchFn)
    const area = polygonArea(SQUARE)
    const file = await fetchCsv(area, true, 'http://api.test')
    const [url, init] = fetchFn.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://api.test/api/export.csv')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ polygon: SQUARE })
    expect(file.filename).toBe('SYNTHETIC_x.csv')
  })

  it('keeps GET for a rectangle', async () => {
    const fetchFn = vi.fn().mockResolvedValue(new Response('a'))
    vi.stubGlobal('fetch', fetchFn)
    await fetchCsv({ entity_type: 'CUSTOM', entity_id: 'x', bbox: [99, 0, 101, 1] }, true, 'http://api.test')
    expect(fetchFn).toHaveBeenCalledWith('http://api.test/api/export.csv?bbox=99%2C0%2C101%2C1')
  })
})
