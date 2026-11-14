import { Suspense, lazy, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, fetchAnomalies, fetchEntities, fetchMapCells, fetchMeta } from './api/client.ts'
import type { Anomaly, Bbox, EntityItem, MapCell } from './api/contract.ts'
import { AnomalyPanel } from './components/anomalies/AnomalyPanel.tsx'
import { EXPANDED_SIZE, PAGE_SIZE, outlinedCountries, rankAnomalies, topN } from './components/anomalies/rankings.ts'
import type { RankingTab } from './components/anomalies/rankings.ts'
import { AreaPicker } from './components/area/AreaPicker.tsx'
import { resolveArea } from './components/area/resolveArea.ts'
import { useAreaSeries } from './components/area/useAreaSeries.ts'
import { useStaticManifest } from './api/staticData.ts'
import { OfflineNote } from './components/common/OfflineNote.tsx'
import { NO_OFFLINE_MAP, offlineMapNote } from './content/offline.ts'
import { EmptyState, ErrorState, LoadingState } from './components/common/States.tsx'
import { PAGE_PARAM, METHODS_PAGE, methodsHref, pageFromSearch } from './content/methodsLink.ts'
import { RAW_ONLY_NOTE, RawOnlyContext, isRawOnly, isRawOnlySeries } from './content/rawOnly.ts'
import { SyntheticBanner } from './components/common/SyntheticBanner.tsx'
import { SourceToggle } from './components/common/SourceToggle.tsx'
import { CellInfo } from './components/map/CellInfo.tsx'
import { Legend } from './components/map/Legend.tsx'
import { MapModeSelector } from './components/map/MapModeSelector.tsx'
import { CalendarPanel } from './components/calendar/CalendarPanel.tsx'
import { EvidencePanel } from './components/evidence/EvidencePanel.tsx'
import { WitnessPanel } from './components/witness/WitnessPanel.tsx'
import { MonthSelector } from './components/map/MonthSelector.tsx'
import { sharedMax } from './components/map/scale.ts'
import { hasOfflineMap, monthKey, monthRange, offlineMapMonths } from './state/months.ts'
import { customArea } from './state/bbox.ts'
import { effectiveLayer, rawAvailable, selectionReducer } from './state/selection.ts'
import { encodeSelection, selectionFromUrl } from './state/urlState.ts'

const MethodsPage = lazy(() => import('./components/methods/MethodsPage.tsx').then((m) => ({ default: m.MethodsPage })))
// The map (MapLibre, deck.gl and the draw tool) is loaded when first needed, so the first load is small (T-042).
const MapView = lazy(() => import('./components/map/MapView.tsx').then((m) => ({ default: m.MapView })))

export default function App() {
  // The selection starts from the link (area, month, source, map mode, value mode), if any.
  const [selection, dispatch] = useReducer(selectionReducer, null, () => selectionFromUrl(window.location.search))
  const [page, setPage] = useState<'map' | 'methods'>(() => pageFromSearch(window.location.search))
  const [drawing, setDrawing] = useState(false)
  const [anomalyTab, setAnomalyTab] = useState<RankingTab>('COUNTRY')
  const [anomalyExpanded, setAnomalyExpanded] = useState(false)

  // Keep the link in step with the selection, so the address bar can be shared.
  useEffect(() => {
    const params = new URLSearchParams(encodeSelection(selection))
    if (page === 'methods') params.set(PAGE_PARAM, METHODS_PAGE)
    const query = params.toString()
    const url = `${window.location.pathname}${query === '' ? '' : `?${query}`}${window.location.hash}`
    window.history.replaceState(null, '', url)
  }, [selection, page])

  const countries = useQuery({ queryKey: ['entities', 'COUNTRY'], queryFn: () => fetchEntities('COUNTRY'), retry: false })
  const continents = useQuery({ queryKey: ['entities', 'CONTINENT'], queryFn: () => fetchEntities('CONTINENT'), retry: false })
  const area = resolveArea(selection.area, countries.data, continents.data)
  const customSeries = useAreaSeries(area, { enabled: area.entity_type === 'CUSTOM' })
  const customError = customSeries.error instanceof ApiError ? customSeries.error : null
  const customMessage =
    area.entity_type === 'CUSTOM' && customSeries.isError
      ? (customError?.detail ?? 'Data are not available right now. The custom area could not be loaded.')
      : null

  const chooseEntity = (item: EntityItem) =>
    dispatch({
      type: 'select-entity',
      entity: {
        entity_type: item.entity_type === 'CONTINENT' ? 'CONTINENT' : 'COUNTRY',
        entity_id: item.entity_id,
        entity_name: item.entity_name,
      },
      fit: item.bbox,
    })
  // The global anomaly overview (T-040): the API's anomalies for the selected month, ranked per
  // verdict and per area type here. The world is a single entity and is left out.
  const anomalies = useQuery({
    queryKey: ['anomalies', selection.month?.year, selection.month?.month],
    queryFn: () => fetchAnomalies(selection.month!.year, selection.month!.month),
    enabled: selection.month !== null,
    retry: false,
  })
  const rankings = useMemo(() => rankAnomalies(anomalies.data ?? [], anomalyTab), [anomalies.data, anomalyTab])
  const anomalyShown = anomalyExpanded ? EXPANDED_SIZE : PAGE_SIZE
  const anomalyOutlines = useMemo(
    () =>
      anomalyTab === 'COUNTRY'
        ? outlinedCountries(topN(rankings.above, anomalyShown), topN(rankings.below, anomalyShown))
        : { above: [], below: [] },
    [anomalyTab, rankings, anomalyShown],
  )
  const anomalyStatus =
    selection.month === null ? 'idle' : anomalies.isPending ? 'loading' : anomalies.isError ? 'error' : 'ready'
  const anomalyList = anomalyTab === 'COUNTRY' ? countries.data : continents.data
  const chooseAnomaly = (anomaly: Anomaly) => {
    const found = anomalyList?.find((e) => e.entity_id === anomaly.entity_id)
    dispatch({
      type: 'select-entity',
      entity: {
        entity_type: anomaly.entity_type === 'CONTINENT' ? 'CONTINENT' : 'COUNTRY',
        entity_id: anomaly.entity_id,
        entity_name: anomaly.entity_name,
      },
      fit: found?.bbox,
    })
    evidenceHeading.current?.focus()
  }

  const chooseCustom = (bbox: Bbox) => {
    setDrawing(false)
    dispatch({ type: 'select-entity', entity: customArea(bbox) })
  }

  // True while the app shows the offline copy of the preset views (T-043).
  const offline = useStaticManifest()
  const meta = useQuery({ queryKey: ['meta'], queryFn: () => fetchMeta(), retry: false })
  const months = useMemo(
    () =>
      meta.data === undefined
        ? []
        : monthRange(meta.data.first_month, meta.data.latest_month, meta.data.provisional_months),
    [meta.data],
  )

  // The offline copy may have the map for some months only (a web-host copy): the month picker lists
  // those, and a month without a map says so. The calendar, series, evidence and CSVs cover every month.
  const mapMonths = useMemo(() => offlineMapMonths(months, offline?.months ?? null), [months, offline])
  const offlineMapNoteText = offline === null ? null : offlineMapNote(offline, months)
  const mapAvailable = hasOfflineMap(offline?.months ?? null, selection.month)

  // Start on the latest month once the available months are known.
  useEffect(() => {
    const latest = months[months.length - 1]
    if (selection.month === null && latest !== undefined) {
      dispatch({ type: 'set-month', year: latest.year, month: latest.month })
    }
  }, [months, selection.month])

  // The API layer follows the shared Raw / Harmonized control and the map mode.
  // Raw-only products have no harmonized values: the views show raw activity and say so.
  const rawOnly = isRawOnly(meta.data)
  // The note is decided per series: preset areas are raw-only for now, a custom-area series is
  // harmonized and carries no raw-only note (it is hidden while that series is still loading).
  const areaSeries = useAreaSeries(area)
  const noteShown =
    rawOnly && (area.entity_type === 'CUSTOM' ? false : isRawOnlySeries(areaSeries.data, rawOnly))
  const layer = effectiveLayer(rawOnly ? { ...selection, source: 'raw', mapMode: 'activity' } : selection)
  const cells = useQuery({
    queryKey: ['map', selection.month?.year, selection.month?.month, layer],
    queryFn: () => fetchMapCells(selection.month!.year, selection.month!.month, layer),
    enabled: selection.month !== null && page === 'map' && mapAvailable,
    retry: false,
  })

  // Clicking a calendar cell sets the month and moves focus to the evidence panel's heading.
  const evidenceHeading = useRef<HTMLHeadingElement>(null)

  const cellList: readonly MapCell[] | null = cells.data ?? null
  const max = cellList === null ? 0 : sharedMax(cellList)
  const selectedCell =
    selection.entity?.entity_type === 'CELL'
      ? (cellList?.find((c) => c.cell_id === selection.entity?.entity_id) ?? null)
      : null

  return (
    <RawOnlyContext.Provider value={rawOnly}>
    <div className="app">
      <a className="skip-link" href="#main-content">
        Skip to the controls and the map
      </a>
      <SyntheticBanner synthetic={meta.data?.synthetic === true} />
      <OfflineNote manifest={offline} mapNote={offlineMapNoteText} />
      <header>
        <h1>Global Fire Harmonization</h1>
        <p className="subtitle">Satellite-detected fire activity, harmonized across MODIS and VIIRS</p>
        {page === 'map' && (
          <a
            className="methods-link"
            href={methodsHref()}
            onClick={(e) => {
              e.preventDefault()
              setPage('methods')
              window.scrollTo(0, 0)
            }}
          >
            Methods and validation
          </a>
        )}
      </header>
      {page === 'map' && noteShown && (
        <p className="raw-only-note" role="status">
          {RAW_ONLY_NOTE}
        </p>
      )}
      {page === 'methods' ? (
        <Suspense fallback={<LoadingState what="the methods page" />}>
          <MethodsPage
            onBack={() => {
              setPage('map')
              window.scrollTo(0, 0)
            }}
          />
        </Suspense>
      ) : (
      <main id="main-content" tabIndex={-1}>
        <div className="controls">
          <MonthSelector
            months={mapMonths}
            value={selection.month}
            onChange={(year, month) => dispatch({ type: 'set-month', year, month })}
          />
          <SourceToggle
            value={rawOnly ? 'raw' : selection.source}
            onChange={(source) => dispatch({ type: 'set-source', source })}
            rawDisabled={!rawOnly && !rawAvailable(selection.valueMode)}
            harmonizedDisabled={rawOnly}
          />
          <MapModeSelector
            value={rawOnly ? 'activity' : selection.mapMode}
            onChange={(mapMode) => dispatch({ type: 'set-map-mode', mapMode })}
            verdictDisabled={rawOnly}
          />
        </div>
        <div className="map-area">
          <Suspense fallback={<LoadingState what="the map" />}>
          <MapView
            cells={cellList}
            layer={layer}
            selectedCellId={selection.entity?.entity_type === 'CELL' ? selection.entity.entity_id : null}
            selectedCountryIso3={selection.entity?.entity_type === 'COUNTRY' ? selection.entity.entity_id : null}
            onSelectCell={(cell) =>
              dispatch({ type: 'select-entity', entity: { entity_type: 'CELL', entity_id: cell.cell_id, entity_name: cell.cell_id } })
            }
            onSelectCountry={(iso3, name) =>
              dispatch({ type: 'select-entity', entity: { entity_type: 'COUNTRY', entity_id: iso3, entity_name: name } })
            }
            fit={selection.fit}
            customBbox={area.entity_type === 'CUSTOM' ? area.bbox : null}
            drawing={drawing}
            onDrawn={chooseCustom}
            anomalyOutlines={anomalyOutlines}
          />
          </Suspense>
          <aside>
            <AreaPicker
              area={area}
              countries={countries.data}
              continents={continents.data}
              listsFailed={countries.isError || continents.isError}
              onChooseEntity={chooseEntity}
              onChooseWorld={() => dispatch({ type: 'clear-entity' })}
              onChooseCustom={chooseCustom}
              drawing={drawing}
              onToggleDrawing={() => setDrawing((d) => !d)}
              customMessage={customMessage}
              customLoading={area.entity_type === 'CUSTOM' && customSeries.isFetching}
              synthetic={meta.data?.synthetic === true}
            />
            <AnomalyPanel
              month={selection.month}
              provisional={
                selection.month !== null &&
                (meta.data?.provisional_months ?? []).includes(monthKey(selection.month.year, selection.month.month))
              }
              status={anomalyStatus}
              onRetry={() => void anomalies.refetch()}
              tab={anomalyTab}
              onTabChange={(t) => {
                setAnomalyTab(t)
                setAnomalyExpanded(false)
              }}
              expanded={anomalyExpanded}
              onToggleExpanded={() => setAnomalyExpanded((e) => !e)}
              rankings={rankings}
              totalAreas={anomalyList === undefined ? null : anomalyList.length}
              onSelect={chooseAnomaly}
            />
            <Legend layer={layer} max={max} />
            <section aria-label="Selection" className="selection">
              <h2>Selection</h2>
              {selection.entity === null && <EmptyState message="Select a cell or a country on the map, or choose an area above." />}
              {selection.entity !== null && selection.entity.entity_type !== 'CELL' && (
                <p>{`Area: ${area.entity_name}${area.entity_type === 'CUSTOM' ? '' : ` (${area.entity_id})`}`}</p>
              )}
              {selectedCell !== null && <CellInfo cell={selectedCell} layer={layer} />}
            </section>
            <section aria-label="Data status" className="status">
              {(meta.isPending || (cells.isPending && mapAvailable)) && selection.month !== null && (
                <LoadingState what="map data" />
              )}
              {!mapAvailable && <EmptyState message={NO_OFFLINE_MAP} />}
              {meta.isPending && <LoadingState what="data information" />}
              {meta.isError && (
                <ErrorState message="Data are not available right now. The country layer still works." onRetry={() => void meta.refetch()} />
              )}
              {cells.isError && mapAvailable && (
                <ErrorState message="The map cells could not be loaded." onRetry={() => void cells.refetch()} />
              )}
              {cellList !== null && cellList.length === 0 && <EmptyState message="No cells for this month." />}
            </section>
          </aside>
        </div>
        <div className="calendar-evidence">
          <CalendarPanel
            area={area}
            meta={meta.data ?? null}
            selectedMonth={selection.month}
            valueMode={rawOnly ? 'activity' : selection.valueMode}
            source={rawOnly ? 'raw' : selection.source}
            onValueModeChange={(valueMode) => dispatch({ type: 'set-value-mode', valueMode })}
            onSelectMonth={(year, month) => {
              dispatch({ type: 'set-month', year, month })
              evidenceHeading.current?.focus()
            }}
            onShowWorld={() => dispatch({ type: 'clear-entity' })}
          />
          <EvidencePanel
            area={area}
            month={selection.month}
            cell={
              selection.entity?.entity_type === 'CELL'
                ? { id: selection.entity.entity_id, record: selectedCell, loading: cells.isPending }
                : null
            }
            meta={meta.data ?? null}
            headingRef={evidenceHeading}
            onShowWorld={() => dispatch({ type: 'clear-entity' })}
          />
        </div>
        <WitnessPanel area={area} onShowWorld={() => dispatch({ type: 'clear-entity' })} />
      </main>
      )}
    </div>
    </RawOnlyContext.Provider>
  )
}
