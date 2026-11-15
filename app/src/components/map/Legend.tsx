import type { MapLayer } from '../../api/contract.ts'
import { VERDICTS } from '../../api/contract.ts'
import { HARMONIZED_DESCRIPTION, RAW_DESCRIPTION } from '../../content/source.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { NO_DATA_COLOR, sequentialColor } from './scale.ts'

const rgb = (c: readonly number[]) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`

/** Short note of the on-map legend; the long notes stay in the sidebar legend. */
export const OVERLAY_ICON_NOTE = 'Icons appear when you zoom in.'

/**
 * The map legend. `overlay` is the compact form drawn on the map (T-071): the same swatches, icons
 * and "no data" cue, with the long explanations left to the sidebar legend and the evidence panel.
 */
export function Legend({ layer, max, overlay = false }: { layer: MapLayer; max: number; overlay?: boolean }) {
  const className = overlay ? 'legend legend-overlay' : 'legend'
  if (layer === 'verdict') {
    return (
      <section className={className} aria-label={overlay ? 'Legend on the map' : 'Map legend'}>
        <h2>Verdict for the month</h2>
        <ul>
          {VERDICTS.map((v) => {
            const p = VERDICT_PRESENTATION[v]
            return (
              <li key={v}>
                <span className="swatch" style={{ background: rgb(p.color) }} aria-hidden="true">
                  {p.icon}
                </span>
                {p.label}
              </li>
            )
          })}
        </ul>
        {overlay ? (
          <p className="legend-note">{OVERLAY_ICON_NOTE}</p>
        ) : (
          <p className="legend-note">
            Each verdict is also given as an icon and text, not colour alone. The icons appear on the
            map when you zoom in far enough for a cell to hold one; the verdict is always in the
            tooltip and in the evidence panel.
          </p>
        )}
      </section>
    )
  }
  const stops = [0, 0.25, 0.5, 0.75, 1].map((t) => rgb(sequentialColor(t * max, max)))
  return (
    <section className={className} aria-label={overlay ? 'Legend on the map' : 'Map legend'}>
      <h2>{layer === 'raw' ? 'Raw combined activity' : 'Harmonized activity'}</h2>
      <div className="ramp" style={{ background: `linear-gradient(to right, ${stops.join(', ')})` }} aria-hidden="true" />
      <div className="ramp-labels">
        <span>0</span>
        <span>{max > 0 ? Math.round(max) : 'no data'}</span>
      </div>
      {!overlay && (
        <p className="legend-note">
          {layer === 'raw' ? RAW_DESCRIPTION : HARMONIZED_DESCRIPTION} Raw and harmonized share this
          colour scale.
        </p>
      )}
      <p className="legend-note">
        <span className="swatch swatch-marked" style={{ background: rgb(NO_DATA_COLOR) }} aria-hidden="true" />
        No data (dark outline)
      </p>
    </section>
  )
}
