import { Suspense, lazy, useMemo, useState } from 'react'
import { ApiError } from '../../api/client.ts'
import type { Metadata } from '../../api/contract.ts'
import type { Area, Source, ValueMode } from '../../state/selection.ts'
import { ErrorBoundary } from '../common/ErrorBoundary.tsx'
import { useAreaSeries } from '../area/useAreaSeries.ts'
import { RAW_ONLY_AREA_UNAVAILABLE, isRawOnlySeries, useRawOnly } from '../../content/rawOnly.ts'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { CalendarLegend } from './CalendarLegend.tsx'
import { CalendarTable } from './CalendarTable.tsx'
import { ValueModeSelector } from './ValueModeSelector.tsx'
import { buildCalendarGrid, maxActivity as seriesMaxActivity } from './grid.ts'

// The chart (ECharts) is loaded when first shown (T-042).
const CalendarChart = lazy(() => import('./CalendarChart.tsx').then((m) => ({ default: m.CalendarChart })))

interface Props {
  area: Area
  meta: Metadata | null
  selectedMonth: { year: number; month: number } | null
  valueMode: ValueMode
  source: Source
  onValueModeChange: (mode: ValueMode) => void
  onSelectMonth: (year: number, month: number) => void
  onShowWorld: () => void
}

/** The historical calendar for the selected area: heatmap or table, with a legend. */
export function CalendarPanel({
  area,
  meta,
  selectedMonth,
  valueMode,
  source,
  onValueModeChange,
  onSelectMonth,
  onShowWorld,
}: Props) {
  const [tableView, setTableView] = useState(false)
  const series = useAreaSeries(area)
  const records = series.data
  const globalRawOnly = useRawOnly()
  const rawOnly = isRawOnlySeries(records, globalRawOnly)
  // % of normal needs a baseline: unavailable when the series holds none (raw-only, or until T-014).
  const pctUnavailable = globalRawOnly && (records === undefined || records.every((r) => r.pct_of_normal === null))
  const rows = useMemo(
    () =>
      records === undefined || meta === null
        ? []
        : buildCalendarGrid(records, meta.first_month, meta.latest_month, meta.provisional_months),
    [records, meta],
  )
  const maxActivity = useMemo(() => (records === undefined ? 0 : seriesMaxActivity(records)), [records])

  const apiError = series.error instanceof ApiError ? series.error : null
  const isCustom = area.entity_type === 'CUSTOM'
  const notFound = apiError?.status === 404 && !isCustom
  // A custom area shows the server's own message (for example a 422 or a 503).
  const serverMessage = isCustom ? (apiError?.detail ?? null) : null

  return (
    <section className="calendar-panel" aria-label="Historical calendar">
      <header className="calendar-header">
        <h2>{`Calendar: ${area.entity_name}`}</h2>
        <ValueModeSelector
          value={valueMode}
          onChange={onValueModeChange}
          pctUnavailable={pctUnavailable}
          rawOnly={rawOnly}
        />
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

      {meta === null && !series.isError && <LoadingState what="data information" />}
      {meta !== null && series.isPending && <LoadingState what="the calendar" />}
      {series.isError && notFound && (
        <div className="state state-error" role="alert">
          <p>Area not found: {area.entity_name}. The calendar is available for the countries, continents and the world that the data cover.</p>
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
      {series.isError && !notFound && serverMessage === null && globalRawOnly && apiError?.status === 503 && (
        <EmptyState message={RAW_ONLY_AREA_UNAVAILABLE} />
      )}
      {series.isError && !notFound && serverMessage === null && !(globalRawOnly && apiError?.status === 503) && (
        <ErrorState
          message="Data are not available right now. The calendar could not be loaded."
          onRetry={() => void series.refetch()}
        />
      )}
      {meta !== null && records !== undefined && records.length === 0 && (
        <EmptyState message="No records for this area." />
      )}
      {meta !== null && records !== undefined && records.length > 0 && (
        <div className="calendar-body">
          <div className="calendar-main">
            {tableView ? (
              <CalendarTable
                rows={rows}
                mode={valueMode}
                maxActivity={maxActivity}
                selected={selectedMonth}
                areaName={area.entity_name}
                source={source}
                onSelectMonth={onSelectMonth}
              />
            ) : (
              <ErrorBoundary
                fallback={
                  <p className="state state-error" role="alert">
                    The chart could not be drawn. Turn on the table view to see the same data.
                  </p>
                }
              >
                <Suspense fallback={<LoadingState what="the chart" />}>
                <CalendarChart
                  rows={rows}
                  mode={valueMode}
                  maxActivity={maxActivity}
                  selected={selectedMonth}
                  areaName={area.entity_name}
                  source={source}
                  onSelectMonth={onSelectMonth}
                />
                </Suspense>
              </ErrorBoundary>
            )}
          </div>
          <CalendarLegend mode={valueMode} maxActivity={maxActivity} source={source} />
        </div>
      )}
    </section>
  )
}
