import type { StaticManifest } from '../../api/staticData.ts'
import { offlineNoteText } from '../../content/offline.ts'

/** A visible notice while the app runs from the static files and not from the API (T-043). */
export function OfflineNote({
  manifest,
  mapNote = null,
}: {
  manifest: StaticManifest | null
  /** Which months have a map, for a copy that has the map for some months only. */
  mapNote?: string | null
}) {
  if (manifest === null) return null
  return (
    <>
      <p className="offline-note" role="status">
        <strong>Offline copy.</strong> {offlineNoteText(manifest)}
      </p>
      {mapNote !== null && (
        <p className="offline-note offline-map-note" role="status">
          {mapNote}
        </p>
      )}
    </>
  )
}
