import { useState } from 'react'
import * as UI from '../../content/ui.ts'
import { GIBS_LINK } from './gibs.ts'
import './imagery.css'

// The Satellite view and Flat / Globe controls live in the dock (components/dock, T-093); the map keeps the credit.

/** Credit and layer date: one small line at the bottom right of the map. The imagery failure note is in the dock. */
export function ImageryCredit({
  offlineCopy,
  satDateShown,
  basemapShown,
}: {
  offlineCopy: boolean
  satDateShown: string | null
  basemapShown: boolean
}) {
  const [info, setInfo] = useState(false)
  return (
    <div className="map-credit">
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
