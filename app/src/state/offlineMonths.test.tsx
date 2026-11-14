import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { StaticManifest } from '../api/staticData.ts'
import { OfflineNote } from '../components/common/OfflineNote.tsx'
import { MonthSelector } from '../components/map/MonthSelector.tsx'
import { NO_OFFLINE_MAP, offlineMapNote } from '../content/offline.ts'
import { hasOfflineMap, monthKey, monthRange, offlineMapMonths } from './months.ts'

// SYNTHETIC test data: the months of a data range and the manifests of two kinds of offline copy
// (T-043): a full copy (every month has a map) and a 24-month copy (`--latest-months 24`, for a web host).
const ALL = monthRange('2002-07', '2026-11', ['2026-08', '2026-09', '2026-10', '2026-11'])
const FULL = ALL.map((m) => monthKey(m.year, m.month))
const LAST24 = FULL.slice(-24)

const manifest = (months: string[]): StaticManifest => ({
  format_version: 1, exported_at: '2026-11-15T10:00:00Z', synthetic: false, contract_version: '0.1.1',
  method_version: '0.1.0', data_snapshot: { zips_downloaded: '2026-11-14' }, months, exports: {},
})

describe('the months with a map in the offline copy', () => {
  it('a full copy, and the live service, keep every month', () => {
    expect(offlineMapMonths(ALL, FULL)).toHaveLength(ALL.length)
    expect(offlineMapMonths(ALL, null)).toEqual(ALL)
    expect(offlineMapNote(manifest(FULL), ALL)).toBeNull()
  })

  it('a 24-month copy lists only its 24 months, in order, keeping the provisional marks', () => {
    const months = offlineMapMonths(ALL, LAST24)
    expect(months).toHaveLength(24)
    expect(monthKey(months[0]!.year, months[0]!.month)).toBe('2024-12')
    expect(monthKey(months[23]!.year, months[23]!.month)).toBe('2026-11')
    expect(months.filter((m) => m.provisional)).toHaveLength(4)
  })

  it('says which months have a map when the copy has fewer than the data', () => {
    expect(offlineMapNote(manifest(LAST24), ALL)).toBe(
      'Offline copy: map available for December 2024–November 2026; the calendar and charts cover every month.',
    )
  })

  it('knows whether a month has a map: always on the live service, by the manifest offline', () => {
    expect(hasOfflineMap(null, { year: 2003, month: 5 })).toBe(true)
    expect(hasOfflineMap(LAST24, { year: 2026, month: 10 })).toBe(true)
    expect(hasOfflineMap(LAST24, { year: 2003, month: 5 })).toBe(false)
    expect(hasOfflineMap(LAST24, null)).toBe(true)
    expect(NO_OFFLINE_MAP).toContain('No offline map for this month')
  })
})

describe('the month picker in a 24-month copy', () => {
  const months = offlineMapMonths(ALL, LAST24)
  const picker = (value: { year: number; month: number } | null) =>
    renderToString(<MonthSelector months={months} value={value} onChange={() => {}} />)

  it('lists only the months with a map, so the first listed month cannot go back', () => {
    const html = picker({ year: 2024, month: 12 })
    expect(html).toContain('December 2024')
    expect(html).toMatch(/<button[^>]*disabled[^>]*aria-label="Previous month"|<button[^>]*aria-label="Previous month"[^>]*disabled/)
    expect(html).toContain('max="23"')
  })

  it('shows a month chosen in the calendar that has no map, and can still step to the nearest map months', () => {
    const html = picker({ year: 2010, month: 3 })
    expect(html).toContain('March 2010 (no offline map)')
    expect(html).not.toMatch(/<button[^>]*disabled[^>]*aria-label="Next month"|<button[^>]*aria-label="Next month"[^>]*disabled/)
    // Before the first map month there is nothing earlier to step back to.
    expect(html).toMatch(/<button[^>]*disabled[^>]*aria-label="Previous month"|<button[^>]*aria-label="Previous month"[^>]*disabled/)
  })
})

describe('the offline notices', () => {
  it('shows the map note as its own notice only for a partial copy', () => {
    const partial = renderToString(<OfflineNote manifest={manifest(LAST24)} mapNote={offlineMapNote(manifest(LAST24), ALL)} />)
    expect(partial).toContain('map available for December 2024–November 2026')
    const full = renderToString(<OfflineNote manifest={manifest(FULL)} mapNote={offlineMapNote(manifest(FULL), ALL)} />)
    expect(full).not.toContain('map available for')
    expect(full).toContain('Offline copy.')
  })
})
