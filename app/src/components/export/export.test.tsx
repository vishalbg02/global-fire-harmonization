import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  exportQuery,
  fallbackFilename,
  fetchCsv,
  filenameFromDisposition,
} from '../../api/client.ts'
import { ExportButton } from './ExportButton.tsx'
import { EXPORT_NOTE, FIRMS_URL, exportErrorMessage } from './exportHelpers.ts'

// SYNTHETIC test data. Not NASA observations.
const IDN = { entity_type: 'COUNTRY' as const, entity_id: 'IDN', entity_name: 'Indonesia' }
const CUSTOM = {
  entity_type: 'CUSTOM' as const,
  entity_id: 'custom_x',
  entity_name: 'Custom area',
  bbox: [99, 0, 101, 1] as [number, number, number, number],
}

afterEach(() => vi.unstubAllGlobals())

describe('export request', () => {
  it('builds the preset query', () => {
    expect(exportQuery(IDN)).toBe('entity_type=COUNTRY&entity_id=IDN')
  })

  it('builds the custom query as W,S,E,N', () => {
    expect(exportQuery(CUSTOM)).toBe('bbox=99%2C0%2C101%2C1')
  })

  it('reads the file name from Content-Disposition', () => {
    expect(filenameFromDisposition('attachment; filename="a_b.csv"')).toBe('a_b.csv')
    expect(filenameFromDisposition('attachment; filename=a.csv')).toBe('a.csv')
    expect(filenameFromDisposition(null)).toBeNull()
    expect(filenameFromDisposition('attachment')).toBeNull()
  })

  it('uses a SYNTHETIC-marked fallback name only while the data are synthetic', () => {
    expect(fallbackFilename(IDN, true)).toBe('SYNTHETIC_fire-harmonization_COUNTRY_IDN.csv')
    expect(fallbackFilename(IDN, false)).toBe('fire-harmonization_COUNTRY_IDN.csv')
  })
})

describe('fetchCsv', () => {
  it('requests the URL and returns the blob and the server file name', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('a,b\r\n', { headers: { 'Content-Disposition': 'attachment; filename="x.csv"' } }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const file = await fetchCsv(IDN, true, 'http://api')
    expect(fetchMock).toHaveBeenCalledWith('http://api/api/export.csv?entity_type=COUNTRY&entity_id=IDN')
    expect(file.filename).toBe('x.csv')
    expect(await file.blob.text()).toBe('a,b\r\n')
  })

  it('falls back to a generated name when the header is missing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('a')))
    expect((await fetchCsv(IDN, true, '')).filename).toBe('SYNTHETIC_fire-harmonization_COUNTRY_IDN.csv')
  })

  it('carries the server message on a 503', async () => {
    const body = JSON.stringify({ detail: 'Custom areas are not available yet.' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 503 })))
    const error = await fetchCsv(CUSTOM, true, '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
    expect(exportErrorMessage(error)).toBe('Custom areas are not available yet.')
  })

  it('reports a 400 and a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 400 })))
    expect(exportErrorMessage(await fetchCsv(IDN, true, '').catch((e: unknown) => e))).toContain('status 400')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('x')))
    const error = await fetchCsv(IDN, true, '').catch((e: unknown) => e)
    expect((error as ApiError).status).toBeNull()
    expect(exportErrorMessage(error)).toBe('The data service could not be reached.')
  })
})

describe('ExportButton', () => {
  it('shows the button with the area name, the note and the FIRMS link', () => {
    const html = renderToString(<ExportButton area={IDN} synthetic />)
    expect(html).toContain('Download CSV: Indonesia')
    expect(html).toContain(EXPORT_NOTE.replace(/'/g, '&#x27;'))
    expect(html).toContain(FIRMS_URL)
    expect(html).not.toContain('role="alert"')
  })
})
