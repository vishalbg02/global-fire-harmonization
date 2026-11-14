import { useState } from 'react'
import { ApiError } from '../../api/client.ts'
import type { Area } from '../../state/selection.ts'
import { JUMP_CAPTION } from '../../content/source.ts'
import { useAreaSeries } from '../area/useAreaSeries.ts'
import { ErrorBoundary } from '../common/ErrorBoundary.tsx'
import { RAW_ONLY_AREA_UNAVAILABLE, useRawOnly } from '../../content/rawOnly.ts'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { SatelliteTimeline } from './SatelliteTimeline.tsx'
import { WitnessChart } from './WitnessChart.tsx'
import { WitnessTable } from './WitnessTable.tsx'

interface Props {
  area: Area
  onShowWorld: () => void
}

/**
 * The witness comparison chart (T-037): the area's whole monthly history, the satellite
 * timeline, and the one-sentence explanation of why raw counts jump. Shares the same series
 * query as the calendar (useAreaSeries), so selecting an area triggers no extra request.
 */
export function WitnessPanel({ area, onShowWorld }: Props) {
  const [tableView, setTableView] = useState(false)
  const series = useAreaSeries(area)
  const rawOnly = useRawOnly()
  const records = series.data

  const apiError = series.error instanceof ApiError ? series.error : null
  const isCustom = area.entity_type === 'CUSTOM'
  const notFound = apiError?.status === 404 && !isCustom
  // A custom area shows the server's own message (for example a 422 or a 503), as the calendar does.
  const serverMessage = isCustom ? (apiError?.detail ?? null) : null

  return (
    <section className="witness-panel" aria-label="Satellite comparison">
      <header className="calendar-header">
        <h2>{`Satellites: ${area.entity_name}`}</h2>
        <label className="table-toggle">
          <input type="checkbox" checked={tableView} onChange={(e) => setTableView(e.target.checked)} />
          Table view
        </label>
        {area.entity_type !== 'GLOBAL' && (
          <button type="button" onClick={onShowWorld}>
            Show the world
          </button>
        )}
      </header>

      <p className="legend-note">{JUMP_CAPTION}</p>
      <p className="legend-note">
        Marks on the chart (and the Notes column of the table): a red vertical line marks an
        outage month; a purple dashed line marks an Aqua-drift-era month; an olive dotted line
        marks a provisional month.
      </p>

      {rawOnly && (
        <p className="source-note">
          The harmonized line, its band and the baseline are not available yet (raw data only). The raw lines are real.
        </p>
      )}
      {series.isPending && <LoadingState what="the satellite comparison" />}
      {series.isError && notFound && (
        <div className="state state-error" role="alert">
          <p>{`Area not found: ${area.entity_name}. The satellite comparison is available for the countries, continents and the world that the data cover.`}</p>
          {area.entity_type !== 'GLOBAL' && (
            <button type="button" onClick={onShowWorld}>
              Show the world
            </button>
          )}
        </div>
      )}
      {series.isError && serverMessage !== null && (
        <ErrorState message={serverMessage} onRetry={apiError?.status === 422 ? undefined : () => void series.refetch()} />
      )}
      {series.isError && !notFound && serverMessage === null && rawOnly && apiError?.status === 503 && (
        <EmptyState message={RAW_ONLY_AREA_UNAVAILABLE} />
      )}
      {series.isError && !notFound && serverMessage === null && !(rawOnly && apiError?.status === 503) && (
        <ErrorState
          message="Data are not available right now. The satellite comparison could not be loaded."
          onRetry={() => void series.refetch()}
        />
      )}
      {records !== undefined && records.length === 0 && <EmptyState message="No records for this area." />}
      {records !== undefined && records.length > 0 && (
        <div className="witness-body">
          {tableView ? (
            <WitnessTable records={records} areaName={area.entity_name} />
          ) : (
            <ErrorBoundary
              fallback={
                <p className="state state-error" role="alert">
                  The chart could not be drawn. Turn on the table view to see the same data.
                </p>
              }
            >
              <WitnessChart records={records} areaName={area.entity_name} />
            </ErrorBoundary>
          )}
          <SatelliteTimeline />
        </div>
      )}
    </section>
  )
}
