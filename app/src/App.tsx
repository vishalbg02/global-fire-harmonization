import { useEffect, useMemo, useReducer } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMapCells, fetchMeta } from './api/client.ts'
import type { MapCell } from './api/contract.ts'
import { EmptyState, ErrorState, LoadingState } from './components/common/States.tsx'
import { SyntheticBanner } from './components/common/SyntheticBanner.tsx'
import { CellInfo } from './components/map/CellInfo.tsx'
import { LayerSelector } from './components/map/LayerSelector.tsx'
import { Legend } from './components/map/Legend.tsx'
import { MapView } from './components/map/MapView.tsx'
import { CalendarPanel } from './components/calendar/CalendarPanel.tsx'
import { MonthSelector } from './components/map/MonthSelector.tsx'
import { sharedMax } from './components/map/scale.ts'
import { monthRange } from './state/months.ts'
import { initialSelection, selectionReducer } from './state/selection.ts'

export default function App() {
  const [selection, dispatch] = useReducer(selectionReducer, initialSelection)

  const meta = useQuery({ queryKey: ['meta'], queryFn: () => fetchMeta(), retry: false })
  const months = useMemo(
    () =>
      meta.data === undefined
        ? []
        : monthRange(meta.data.first_month, meta.data.latest_month, meta.data.provisional_months),
    [meta.data],
  )

  // Start on the latest month once the available months are known.
  useEffect(() => {
    const latest = months[months.length - 1]
    if (selection.month === null && latest !== undefined) {
      dispatch({ type: 'set-month', year: latest.year, month: latest.month })
    }
  }, [months, selection.month])

  const cells = useQuery({
    queryKey: ['map', selection.month?.year, selection.month?.month, selection.layer],
    queryFn: () => fetchMapCells(selection.month!.year, selection.month!.month, selection.layer),
    enabled: selection.month !== null,
    retry: false,
  })

  const cellList: readonly MapCell[] | null = cells.data ?? null
  const max = cellList === null ? 0 : sharedMax(cellList)
  const selectedCell =
    selection.entity?.entity_type === 'CELL'
      ? (cellList?.find((c) => c.cell_id === selection.entity?.entity_id) ?? null)
      : null

  return (
    <div className="app">
      <SyntheticBanner synthetic={meta.data?.synthetic === true} />
      <header>
        <h1>Global Fire Harmonization</h1>
        <p className="subtitle">Satellite-detected fire activity, harmonized across MODIS and VIIRS</p>
      </header>
      <main>
        <div className="controls">
          <MonthSelector
            months={months}
            value={selection.month}
            onChange={(year, month) => dispatch({ type: 'set-month', year, month })}
          />
          <LayerSelector value={selection.layer} onChange={(layer) => dispatch({ type: 'set-layer', layer })} />
        </div>
        <div className="map-area">
          <MapView
            cells={cellList}
            layer={selection.layer}
            selectedCellId={selection.entity?.entity_type === 'CELL' ? selection.entity.entity_id : null}
            selectedCountryIso3={selection.entity?.entity_type === 'COUNTRY' ? selection.entity.entity_id : null}
            onSelectCell={(cell) =>
              dispatch({ type: 'select-entity', entity: { entity_type: 'CELL', entity_id: cell.cell_id, entity_name: cell.cell_id } })
            }
            onSelectCountry={(iso3, name) =>
              dispatch({ type: 'select-entity', entity: { entity_type: 'COUNTRY', entity_id: iso3, entity_name: name } })
            }
          />
          <aside>
            <Legend layer={selection.layer} max={max} />
            <section aria-label="Selection" className="selection">
              <h2>Selection</h2>
              {selection.entity === null && <EmptyState message="Select a cell or a country on the map." />}
              {selection.entity?.entity_type === 'COUNTRY' && (
                <p>
                  Country: {selection.entity.entity_name} ({selection.entity.entity_id}). Country series are added in a
                  later task.
                </p>
              )}
              {selectedCell !== null && <CellInfo cell={selectedCell} />}
            </section>
            <section aria-label="Data status" className="status">
              {(meta.isPending || cells.isPending) && selection.month !== null && <LoadingState what="map data" />}
              {meta.isPending && <LoadingState what="data information" />}
              {meta.isError && (
                <ErrorState message="Data are not available right now. The country layer still works." onRetry={() => void meta.refetch()} />
              )}
              {cells.isError && <ErrorState message="The map cells could not be loaded." onRetry={() => void cells.refetch()} />}
              {cellList !== null && cellList.length === 0 && <EmptyState message="No cells for this month." />}
            </section>
          </aside>
        </div>
        <CalendarPanel
          area={selection.area}
          meta={meta.data ?? null}
          selectedMonth={selection.month}
          valueMode={selection.valueMode}
          onValueModeChange={(valueMode) => dispatch({ type: 'set-value-mode', valueMode })}
          onSelectMonth={(year, month) => dispatch({ type: 'set-month', year, month })}
          onShowWorld={() => dispatch({ type: 'clear-entity' })}
        />
      </main>
    </div>
  )
}
