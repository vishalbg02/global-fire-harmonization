import { describe, expect, it } from 'vitest'
import { DATA_LEVEL_TEXT, SOURCE_HREF, mapFooterSegments, monthSourceSegments, segmentsText, CALENDAR_CAPTION_ACTIVITY, CALENDAR_CAPTION_PCT, CALENDAR_CAPTION_RAW, WITNESS_CHART_CAPTION } from './sources.ts'

const META = {
  method_version: '0.1.0',
  first_month: '2002-07',
  latest_month: '2026-11',
  provisional_months: ['2026-08', '2026-09', '2026-10', '2026-11'],
  grid: { analysis_deg: 0.5 },
  data_snapshot: { zips_downloaded: '2026-11-14', api_pulled: '2026-11-14' },
}

describe('source lines (T-076)', () => {
  it('writes the map footer from the metadata, with every date and version taken from it', () => {
    const text = segmentsText(mapFooterSegments(META))
    expect(text).toBe(
      'Data: NASA FIRMS MODIS Collection 6.1 and VIIRS 375 m (S-NPP, NOAA-20) active-fire detections; archive (SP) before 2026-08, near-real-time (NRT, provisional) from 2026-08 to 2026-11; analysis grid 0.5°; downloaded 2026-11-14. Harmonized by this project, method 0.1.0.',
    )
    const other = segmentsText(mapFooterSegments({ ...META, method_version: '0.2.0', provisional_months: ['2027-01'], latest_month: '2027-01' }))
    expect(other).toContain('method 0.2.0')
    expect(other).toContain('before 2027-01')
    expect(other).not.toContain('2026-08')
  })

  it('has no provisional months and no optional fields without inventing them', () => {
    const text = segmentsText(mapFooterSegments({ method_version: '0.1.0', first_month: '2002-07', latest_month: '2025-12', provisional_months: [] }))
    expect(text).toContain('archive (SP) through 2025-12')
    expect(text).not.toContain('grid')
    expect(text).not.toContain('downloaded')
    expect(text).not.toContain('undefined')
  })

  it('links only to the sources of docs/DATA_SOURCES.md section 9', () => {
    const allowed = new Set<string>(Object.values(SOURCE_HREF))
    for (const seg of mapFooterSegments(META)) {
      if (seg.href !== undefined) expect(allowed.has(seg.href)).toBe(true)
    }
    for (const href of allowed) expect(href).toMatch(/^https:\/\/(www\.earthdata\.nasa\.gov\/data\/tools\/firms|doi\.org\/10\.5067\/)/)
  })

  it('names the satellites and the data level of a month and links to how the verdict is made', () => {
    const segs = monthSourceSegments(
      { witnesses_used: ['AQUA_MODIS', 'SNPP_VIIRS'], data_level: 'NRT' },
      { pathname: '/', search: '?area=GLOBAL' },
    )
    const text = segmentsText(segs)
    expect(text).toContain('Aqua MODIS, S-NPP VIIRS')
    expect(text).toContain(DATA_LEVEL_TEXT.NRT)
    expect(segs.at(-1)?.href).toBe('/?area=GLOBAL&page=methods#baseline-verdicts')
    expect(segmentsText(monthSourceSegments({ witnesses_used: [], data_level: 'SP' }, { pathname: '/', search: '' }))).toContain('no satellite contributed usable data')
  })

  it('states a unit and a source in every caption, in a plain voice', () => {
    for (const caption of [CALENDAR_CAPTION_ACTIVITY, CALENDAR_CAPTION_PCT, CALENDAR_CAPTION_RAW, WITNESS_CHART_CAPTION]) {
      expect(caption).toMatch(/Source: NASA FIRMS/)
      expect(caption).toMatch(/cell-days|percentage/)
      expect(caption).not.toContain('!')
      expect(caption.toLowerCase()).not.toMatch(/powerful|seamless|cutting-edge|revolution|unlock|leverage|amazing/)
    }
  })
})
