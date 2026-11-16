import { useState } from 'react'
import { fetchCsv } from '../../api/client.ts'
import { STATIC_CUSTOM_MESSAGE, useStaticManifest } from '../../api/staticData.ts'
import type { ExportArea } from '../../api/client.ts'
import { CSV_ABOUT, CSV_BUTTON, CSV_BUTTON_NAME, CSV_FIRMS_LINK, CSV_PREPARING } from '../../content/answer.ts'
import { ErrorState } from '../common/States.tsx'
import { showToast } from '../common/toastStore.ts'
import { EXPORT_NOTE, FIRMS_URL, runExport, saveBlob } from './exportHelpers.ts'

interface Props {
  area: ExportArea & { entity_name: string }
  synthetic: boolean
  /** Replaced in tests. */
  download?: typeof fetchCsv
  save?: typeof saveBlob
  notify?: (message: string) => void
}

/**
 * Download the shown area's monthly series as CSV. The button says "Preparing CSV…" while it works, an error appears
 * below it with Retry, and the toast confirms a download handed to the browser. What the file holds is one click away.
 */
export function ExportButton({ area, synthetic, download = fetchCsv, save = saveBlob, notify = showToast }: Props) {
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle')
  const [message, setMessage] = useState('')
  // A drawn or typed box needs the live service; the preset areas have a CSV in the offline copy.
  const offlineCustom = useStaticManifest() !== null && area.entity_type === 'CUSTOM'

  const run = async () => {
    setState('loading')
    const result = await runExport(area, synthetic, { download, save, notify })
    if (result.ok) {
      setState('idle')
    } else {
      setMessage(result.message)
      setState('error')
    }
  }

  const loading = state === 'loading'
  return (
    <div className="export-csv">
      <button
        type="button"
        className="btn btn-secondary export-btn"
        onClick={() => void run()}
        disabled={loading || offlineCustom}
        aria-label={loading ? undefined : CSV_BUTTON_NAME(area.entity_name)}
      >
        {loading ? CSV_PREPARING : CSV_BUTTON}
      </button>
      {offlineCustom && <p className="legend-note export-offline">{STATIC_CUSTOM_MESSAGE}</p>}
      <details className="export-about">
        <summary>{CSV_ABOUT}</summary>
        <p className="legend-note">{EXPORT_NOTE}</p>
        <p className="legend-note">
          <a href={FIRMS_URL} target="_blank" rel="noreferrer">
            {CSV_FIRMS_LINK}
          </a>
        </p>
      </details>
      {state === 'error' && <ErrorState message={message} onRetry={() => void run()} />}
    </div>
  )
}
