import { useState } from 'react'
import * as UI from '../../content/ui.ts'
import { GIBS_LINK } from './gibs.ts'
import type { ImageryNoteKind } from './gibs.ts'
import './imagery.css'

// The Satellite view and Flat / Globe controls live in the dock (components/dock, T-093); the map keeps the credit.

/** Credit, layer date and the single failure note: one small line at the bottom right of the map. */
export function ImageryCredit({
  offlineCopy,
  satDateShown,
  note,
  basemapShown,
}: {
  offlineCopy: boolean
  satDateShown: string | null
  note: ImageryNoteKind | null
  basemapShown: boolean
}) {
  const [info, setInfo] = useState(false)
  return (
    <div className="map-credit">
      {note !== null && (
        <p className="map-imagery-note" role="status">
          {note === 'offline' ? UI.IMAGERY_NOTE_OFFLINE : UI.IMAGERY_NOTE_FAILED}
        </p>
      )}
      {!offlineCopy && (satDateShown !== null || basemapShown) && (
        <p className="map-credit-line">
          <strong>{satDateShown !== null ? UI.IMAGERY_SAT_DATE(satDateShown) : UI.IMAGERY_BASEMAP_DATE}</strong>
          {'. '}
          <a href={GIBS_LINK} target="_blank" rel="noreferrer" title={UI.IMAGERY_PRIVACY}>
            {UI.IMAGERY_CREDIT}
          </a>{' '}
          <button
            type="button"
            className="bare map-credit-info"
            aria-expanded={info}
            aria-controls="map-credit-privacy"
            aria-label={UI.IMAGERY_CREDIT_INFO}
            onClick={() => setInfo((v) => !v)}
          >
            {'i'}
          </button>
          <span id="map-credit-privacy" hidden={!info} className="map-credit-privacy">
            {' '}
            {UI.IMAGERY_PRIVACY} {UI.IMAGERY_CONTEXT}
          </span>
        </p>
      )}
    </div>
  )
}
