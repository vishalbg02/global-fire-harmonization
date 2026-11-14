import { useState } from 'react'
import { fetchCsv } from '../../api/client.ts'
import { STATIC_CUSTOM_MESSAGE, useStaticManifest } from '../../api/staticData.ts'
import type { ExportArea } from '../../api/client.ts'
import { ErrorState } from '../common/States.tsx'
import { EXPORT_NOTE, FIRMS_URL, exportErrorMessage, saveBlob } from './exportHelpers.ts'

interface Props {
  area: ExportArea & { entity_name: string }
  synthetic: boolean
  /** Replaced in tests. */
  download?: typeof fetchCsv
  save?: typeof saveBlob
}

/** Download the shown area's monthly series as CSV. */
export function ExportButton({ area, synthetic, download = fetchCsv, save = saveBlob }: Props) {
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle')
  const [message, setMessage] = useState('')
  // A drawn or typed box needs the live service; the preset areas have a CSV in the offline copy.
  const offlineCustom = useStaticManifest() !== null && area.entity_type === 'CUSTOM'

  const run = async () => {
    setState('loading')
    try {
      const file = await download(area, synthetic)
      save(file.blob, file.filename)
      setState('idle')
    } catch (error) {
      setMessage(exportErrorMessage(error))
      setState('error')
    }
  }

  return (
    <div className="export-csv">
      <button type="button" onClick={() => void run()} disabled={state === 'loading' || offlineCustom}>
        {state === 'loading' ? 'Preparing CSV…' : `Download CSV: ${area.entity_name}`}
      </button>
      {offlineCustom && <p className="legend-note">{STATIC_CUSTOM_MESSAGE}</p>}
      <p className="legend-note">{EXPORT_NOTE}</p>
      <p className="legend-note">
        <a href={FIRMS_URL} target="_blank" rel="noreferrer">
          Raw hotspot points: NASA FIRMS
        </a>
      </p>
      {state === 'error' && <ErrorState message={message} onRetry={() => void run()} />}
    </div>
  )
}
