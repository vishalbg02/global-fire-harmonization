import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, fetchSeries } from '../../api/client.ts'
import type { Metadata } from '../../api/contract.ts'
import type { Area, Source, ValueMode } from '../../state/selection.ts'
import { ErrorBoundary } from '../common/ErrorBoundary.tsx'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { CalendarChart } from './CalendarChart.tsx'
import { CalendarLegend } from './CalendarLegend.tsx'
import { CalendarTable } from './CalendarTable.tsx'
import { ValueModeSelector } from './ValueModeSelector.tsx'
import { buildCalendarGrid, maxActivity as seriesMaxActivity } from './grid.ts'

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
  const series = useQuery({
    queryKey: ['series', area.entity_type, area.entity_id],
    queryFn: () => fetchSeries(area.entity_type, area.entity_id),
    retry: false,
  })

  const records = series.data
  const rows = useMemo(
    () =>
      records === undefined || meta === null
        ? []
        : buildCalendarGrid(records, meta.first_month, meta.latest_month, meta.provisional_months),
    [records, meta],
  )
  const maxActivity = useMemo(() => (records === undefined ? 0 : seriesMaxActivity(records)), [records])

  const notFound = series.error instanceof ApiError && series.error.status === 404

  return (
    <section className="calendar-panel" aria-label="Historical calendar">
      <header className="calendar-header">
        <h2>Calendar: {area.entity_name}</h2>
        <ValueModeSelector value={valueMode} onChange={onValueModeChange} />
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
      {series.isError && !notFound && (
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
                <CalendarChart
                  rows={rows}
                  mode={valueMode}
                  maxActivity={maxActivity}
                  selected={selectedMonth}
                  areaName={area.entity_name}
                  source={source}
                  onSelectMonth={onSelectMonth}
                />
              </ErrorBoundary>
            )}
          </div>
          <CalendarLegend mode={valueMode} maxActivity={maxActivity} source={source} />
        </div>
      )}
    </section>
  )
}
