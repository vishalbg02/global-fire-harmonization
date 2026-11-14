import { SATELLITE_TIMELINE, SATELLITE_TIMELINE_SOURCE } from '../../content/witnessTimeline.ts'

function formatDate(iso: string): string {
  const date = iso.includes('T') ? iso.slice(0, 10) : iso
  const [y, m, d] = date.split('-')
  return `${d}/${m}/${y}`
}

/** A static reference list of each satellite's operating dates. Not fetched or computed. */
export function SatelliteTimeline() {
  return (
    <section className="satellite-timeline" aria-labelledby="satellite-timeline-title">
      <h3 id="satellite-timeline-title">Satellite timeline</h3>
      <ul>
        {SATELLITE_TIMELINE.map((entry) => (
          <li key={entry.witness}>
            <strong>{entry.label}</strong>
            {`: ${formatDate(entry.start)} – ${entry.end === null ? 'ongoing' : formatDate(entry.end)}`}
            {entry.note !== null && ` (${entry.note})`}
          </li>
        ))}
      </ul>
      <p className="legend-note">{`Source: ${SATELLITE_TIMELINE_SOURCE}.`}</p>
    </section>
  )
}
