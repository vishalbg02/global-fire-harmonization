import type { StaticManifest } from '../api/staticData.ts'
import { monthLabel } from '../state/months.ts'

/** The text of the offline notice: what the copy is, when it was made, and what it lacks (T-043). */
export function offlineNoteText(manifest: StaticManifest): string {
  const snapshot = manifest.data_snapshot
  const when = manifest.exported_at.slice(0, 10)
  const downloaded = snapshot?.zips_downloaded ?? null
  const dataDate = downloaded === null ? '' : ` Data snapshot: ${downloaded}.`
  return `Preset views only, made on ${when}.${dataDate} Custom areas need the live service.`
}

/**
 * The note for a copy whose map covers fewer months than the data (a web-host copy made with
 * `--latest-months`), or null for a full copy. `allMonths` is every month of the data range.
 */
export function offlineMapNote(
  manifest: StaticManifest,
  allMonths: readonly { year: number; month: number }[],
): string | null {
  const first = manifest.months[0]
  const last = manifest.months[manifest.months.length - 1]
  if (first === undefined || last === undefined || manifest.months.length >= allMonths.length) return null
  const name = (ym: string) => monthLabel({ year: Number(ym.slice(0, 4)), month: Number(ym.slice(5, 7)) })
  return `Offline copy: map available for ${name(first)}–${name(last)}; the calendar and charts cover every month.`
}

/** Shown in place of the map when the selected month has none in the offline copy. */
export const NO_OFFLINE_MAP = 'No offline map for this month. The calendar and charts still show it.'
