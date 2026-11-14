import { VERDICTS } from '../../api/contract.ts'
import { ACTIVITY_UNITS } from '../../content/calendar.ts'
import { RAW_DESCRIPTION } from '../../content/source.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import type { Source, ValueMode } from '../../state/selection.ts'
import { NO_DATA_RGB, OUTSIDE_RGB, PCT_CENTRE, PCT_HIGH, PCT_LOW, divergingRgb, sequentialRgb, toCss } from './scales.ts'

function gradient(stops: string[]): string {
  return `linear-gradient(to right, ${stops.join(', ')})`
}

export function CalendarLegend({
  mode,
  maxActivity,
  source = 'harmonized',
}: {
  mode: ValueMode
  maxActivity: number
  source?: Source
}) {
  const raw = source === 'raw'
  const pctStops = [PCT_LOW, 50, PCT_CENTRE, 150, PCT_HIGH].map((v) => toCss(divergingRgb(v)))
  const activityStops = [0, 0.25, 0.5, 0.75, 1].map((t) => toCss(sequentialRgb(t * maxActivity, maxActivity)))
  return (
    <section className="legend calendar-legend" aria-label="Calendar legend">
      <h2>Legend</h2>
      {mode === 'pct' && !raw ? (
        <>
          <div className="ramp" style={{ background: gradient(pctStops) }} aria-hidden="true" />
          <div className="ramp-labels">
            <span>0%</span>
            <span>100% (normal level)</span>
            <span>200% or more</span>
          </div>
          <p className="legend-note">
            % of normal for the month. Colour is clamped at 0% and 200%; tooltips show the true value.
          </p>
        </>
      ) : (
        <>
          <div className="ramp" style={{ background: gradient(activityStops) }} aria-hidden="true" />
          <div className="ramp-labels">
            <span>0</span>
            <span>{maxActivity > 0 ? Math.round(maxActivity) : 'no data'}</span>
          </div>
          <p className="legend-note">
            {raw ? RAW_DESCRIPTION : `Harmonized activity in ${ACTIVITY_UNITS}.`} Raw and harmonized share this colour scale.
          </p>
        </>
      )}
      <ul>
        {!raw &&
          VERDICTS.map((v) => (
            <li key={v}>
              <span className="swatch" aria-hidden="true">
                {VERDICT_PRESENTATION[v].icon}
              </span>
              {VERDICT_PRESENTATION[v].label}
            </li>
          ))}
        <li>
          <span className="swatch" style={{ background: toCss(NO_DATA_RGB) }} aria-hidden="true" />
          No data
        </li>
        <li>
          <span className="swatch" style={{ background: toCss(OUTSIDE_RGB) }} aria-hidden="true" />
          Outside the record
        </li>
        <li>
          <span className="swatch swatch-provisional" aria-hidden="true" />
          Provisional (NRT): may change when science-quality data arrive
        </li>
        <li>
          <span className="swatch swatch-selected" aria-hidden="true" />
          Selected month
        </li>
      </ul>
      <p className="legend-note">
        {raw
          ? 'Raw has no verdict icons: verdicts belong to the harmonized estimate.'
          : 'The icon gives the verdict; the colour gives the value.'}
      </p>
    </section>
  )
}
