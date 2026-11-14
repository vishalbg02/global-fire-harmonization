import type { StaticManifest } from '../api/staticData.ts'

/** The text of the offline notice: what the copy is, when it was made, and what it lacks (T-043). */
export function offlineNoteText(manifest: StaticManifest): string {
  const snapshot = manifest.data_snapshot
  const when = manifest.exported_at.slice(0, 10)
  const downloaded = snapshot?.zips_downloaded ?? null
  const dataDate = downloaded === null ? '' : ` Data snapshot: ${downloaded}.`
  return `Preset views only, made on ${when}.${dataDate} Custom areas need the live service.`
}
