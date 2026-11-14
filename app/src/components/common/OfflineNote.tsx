import type { StaticManifest } from '../../api/staticData.ts'
import { offlineNoteText } from '../../content/offline.ts'

/** A visible notice while the app runs from the static files and not from the API (T-043). */
export function OfflineNote({ manifest }: { manifest: StaticManifest | null }) {
  if (manifest === null) return null
  return (
    <p className="offline-note" role="status">
      <strong>Offline copy.</strong> {offlineNoteText(manifest)}
    </p>
  )
}
