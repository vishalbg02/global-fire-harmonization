import { Suspense, lazy, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, fetchAnomalies, fetchEntities, fetchEvidence, fetchMeta } from './api/client.ts'
import type { Anomaly, Bbox, EntityItem, MapCell } from './api/contract.ts'
import { AnomalyPanel } from './components/anomalies/AnomalyPanel.tsx'
import { EXPANDED_SIZE, PAGE_SIZE, outlinedCountries, rankAnomalies, topN } from './components/anomalies/rankings.ts'
import type { RankingTab } from './components/anomalies/rankings.ts'
import { AreaSearch } from './components/area/AreaSearch.tsx'
import { CustomAreaPanel } from './components/area/CustomAreaPanel.tsx'
import { areaFitBbox, resolveArea } from './components/area/resolveArea.ts'
import { useAreaSeries } from './components/area/useAreaSeries.ts'
import { useStaticManifest } from './api/staticData.ts'
import { applyImageryParams, parseImageryParams } from './components/map/gibs.ts'
import { OfflineNote } from './components/common/OfflineNote.tsx'
import { NO_OFFLINE_MAP, offlineMapNote } from './content/offline.ts'
import { EmptyState, ErrorState, LoadingState } from './components/common/States.tsx'
import { PAGE_PARAM, METHODS_PAGE, pageFromSearch } from './content/methodsLink.ts'
import { RAW_ONLY_AREA_UNAVAILABLE, RAW_ONLY_NOTE, RawOnlyContext, isRawOnly, isRawOnlySeries } from './content/rawOnly.ts'
import { ExportButton } from './components/export/ExportButton.tsx'
import { Header } from './components/layout/Header.tsx'
import { CopyLinkButton } from './components/layout/CopyLinkButton.tsx'
import { StoryChips } from './components/layout/StoryChips.tsx'
import type { FeaturedStory } from './content/featured.ts'
import * as UI from './content/ui.ts'
import { VERDICT_PRESENTATION } from './content/verdicts.ts'
import { TopAnomalies } from './components/anomalies/TopAnomalies.tsx'
import { MapModeSwitch, selectMode } from './components/map/MapModeSwitch.tsx'
import type { SelectMode } from './components/map/MapModeSwitch.tsx'
import { MapSourceLine } from './components/map/MapSourceLine.tsx'
import { SummaryCard } from './components/summary/SummaryCard.tsx'
import { Button } from './components/ui/Button.tsx'
import { Card } from './components/ui/Card.tsx'
import { Tabs } from './components/ui/Tabs.tsx'
import { setTabParam, tabFromSearch } from './state/tabs.ts'
import type { TabId } from './state/tabs.ts'
import { SyntheticBanner } from './components/common/SyntheticBanner.tsx'
import { SourceToggle } from './components/common/SourceToggle.tsx'
import { CellInfo } from './components/map/CellInfo.tsx'
import { MapModeSelector } from './components/map/MapModeSelector.tsx'
import { CalendarPanel } from './components/calendar/CalendarPanel.tsx'
import { EvidencePanel } from './components/evidence/EvidencePanel.tsx'
import { WitnessPanel } from './components/witness/WitnessPanel.tsx'
import { MonthSelector } from './components/map/MonthSelector.tsx'
import { useMapCells } from './state/useMapCells.ts'
import { hasOfflineMap, monthKey, monthRange, offlineMapMonths } from './state/months.ts'
import { customArea } from './state/bbox.ts'
import { useStartMonth } from './state/initialMonth.ts'
import { checkRoundedRing, polygonArea } from './state/polygon.ts'
import type { Ring } from './state/polygon.ts'
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
  const [polygonDrawing, setPolygonDrawing] = useState(false)
  // A polygon drawn on the map: shown in the text box with its reason when it was not accepted.
  const [polygonDraft, setPolygonDraft] = useState<{ ring: Ring; error: string | null; seq: number } | null>(null)
  const [anomalyTab, setAnomalyTab] = useState<RankingTab>('COUNTRY')
  const [anomalyExpanded, setAnomalyExpanded] = useState(false)
  const [tab, setTab] = useState<TabId>(() => tabFromSearch(window.location.search))
  const [drawMenuOpen, setDrawMenuOpen] = useState(false)
  const [hoverCountry, setHoverCountry] = useState<{ iso3: string; name: string } | null>(null)

  // Keep the link in step with the selection, so the address bar can be shared.
  useEffect(() => {
    const params = new URLSearchParams(encodeSelection(selection))
    if (page === 'methods') params.set(PAGE_PARAM, METHODS_PAGE)
    setTabParam(params, tab)
    applyImageryParams(params, parseImageryParams(window.location.search)) // the map's own link choices (T-084)
    const query = params.toString()
    const url = `${window.location.pathname}${query === '' ? '' : `?${query}`}${window.location.hash}`
    window.history.replaceState(null, '', url)
  }, [selection, page, tab])

  const countries = useQuery({ queryKey: ['entities', 'COUNTRY'], queryFn: () => fetchEntities('COUNTRY'), retry: false })
  const continents = useQuery({ queryKey: ['entities', 'CONTINENT'], queryFn: () => fetchEntities('CONTINENT'), retry: false })
  const area = resolveArea(selection.area, countries.data, continents.data)
  // The map shows the selected area, however it was chosen (picker, click on the map, link, typed or
  // drawn): a new request when the area's box changes, or when the same area is asked for again.
  const areaBox = areaFitBbox(area, countries.data, continents.data)
  const areaBoxKey = areaBox === null ? '' : areaBox.join(',')
  const mapFit = useMemo(
    () => (areaBox === null ? selection.fit : { bbox: areaBox }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- areaBoxKey stands for areaBox
    [areaBoxKey, selection.fit],
  )
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
    summaryHeading.current?.focus()
  }

  // Typed or drawn: the same check (the API's rules and messages), then the same selection.
  const choosePolygon = (points: readonly (readonly number[])[]) => {
    setDrawing(false)
    setPolygonDrawing(false)
    const check = checkRoundedRing(points)
    if (check.ok) {
      setPolygonDraft(null)
      dispatch({ type: 'select-entity', entity: polygonArea(check.ring), fit: polygonArea(check.ring).bbox })
    } else {
      setPolygonDraft({
        ring: points.map((p) => [p[0], p[1]]),
        error: check.message,
        seq: (polygonDraft?.seq ?? 0) + 1,
      })
    }
  }

  const chooseCustom = (bbox: Bbox) => {
    setDrawing(false)
    setPolygonDrawing(false)
    setPolygonDraft(null)
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

  // Start on the latest determinable month (a month in the link wins), T-071.
  useStartMonth(months, selection.month, (year, month) => dispatch({ type: 'set-month', year, month }))

  // The API layer follows the shared Raw / Harmonized control and the map mode.
  // Raw-only products have no harmonized values: the views show raw activity and say so.
  const rawOnly = isRawOnly(meta.data)
  // The note is decided per series: preset areas are raw-only for now, a custom-area series is
  // harmonized and carries no raw-only note (it is hidden while that series is still loading).
  const areaSeries = useAreaSeries(area)
  const noteShown =
    rawOnly && (area.entity_type === 'CUSTOM' ? false : isRawOnlySeries(areaSeries.data, rawOnly))
  const layer = effectiveLayer(rawOnly ? { ...selection, source: 'raw', mapMode: 'activity' } : selection)
  const cells = useMapCells({ month: selection.month, layer, enabled: page === 'map' && mapAvailable, months: mapMonths, prefetch: offline === null })

  // Clicking a calendar cell sets the month and moves focus to the evidence panel's heading.
  const evidenceHeading = useRef<HTMLHeadingElement>(null)

  const cellList: readonly MapCell[] | null = cells.data ?? null
  const selectedCell =
    selection.entity?.entity_type === 'CELL'
      ? (cellList?.find((c) => c.cell_id === selection.entity?.entity_id) ?? null)
      : null

  // The summary card focus target (a calendar cell or a ranking entry moves focus to the verdict).
  const summaryHeading = useRef<HTMLHeadingElement>(null)

  // Hovering a country: its verdict for the month, from its stored evidence (the same query the evidence panel uses).
  const hoverEvidence = useQuery({
    queryKey: ['evidence', 'COUNTRY', hoverCountry?.iso3, selection.month?.year, selection.month?.month],
    queryFn: () => fetchEvidence('COUNTRY', hoverCountry!.iso3, selection.month!.year, selection.month!.month),
    enabled: hoverCountry !== null && selection.month !== null && page === 'map',
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const hoverVerdict =
    hoverCountry === null
      ? null
      : hoverEvidence.data !== undefined
        ? `${VERDICT_PRESENTATION[hoverEvidence.data.verdict].icon} ${VERDICT_PRESENTATION[hoverEvidence.data.verdict].label}`
        : hoverEvidence.isPending
          ? UI.HOVER_LOADING
          : UI.HOVER_NO_VERDICT

  const countryRankings = useMemo(() => rankAnomalies(anomalies.data ?? [], 'COUNTRY'), [anomalies.data])
  const drawDisabled = offline !== null
  const onSelectMode = (mode: SelectMode) => {
    setDrawing(mode === 'rectangle')
    setPolygonDrawing(mode === 'polygon')
  }
  const chooseStory = (story: FeaturedStory) => {
    dispatch({ type: 'set-month', year: story.year, month: story.month })
    if (story.entityType === 'GLOBAL') {
      dispatch({ type: 'clear-entity' })
      return
    }
    if (story.entityType === 'FIRE_REGION') return
    const list = story.entityType === 'COUNTRY' ? countries.data : continents.data
    dispatch({
      type: 'select-entity',
      entity: { entity_type: story.entityType, entity_id: story.entityId, entity_name: story.entityName },
      fit: list?.find((e) => e.entity_id === story.entityId)?.bbox,
    })
  }
  const seriesError = areaSeries.error instanceof ApiError ? areaSeries.error : null
  const summaryError =
    area.entity_type === 'CUSTOM'
      ? customMessage
      : seriesError?.status === 404
        ? `Area not found: ${area.entity_name}. The summary is available for the countries, continents and the world that the data cover.`
        : rawOnly && seriesError?.status === 503
          ? RAW_ONLY_AREA_UNAVAILABLE
          : null
  const openMethods = () => {
    setPage('methods')
    window.scrollTo(0, 0)
  }

  return (
    <RawOnlyContext.Provider value={rawOnly}>
    <div className="app">
      <a className="skip-link" href="#main-content">
        Skip to the controls and the map
      </a>
      <SyntheticBanner synthetic={meta.data?.synthetic === true} />
      <OfflineNote manifest={offline} mapNote={offlineMapNoteText} />
      <Header showMethods={page === 'map'} onOpenMethods={openMethods} />
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
        <section className="toolbar" aria-label={UI.TOOLBAR_LABEL}>
          <AreaSearch
            area={area}
            countries={countries.data}
            continents={continents.data}
            listsFailed={countries.isError || continents.isError}
            onChooseEntity={chooseEntity}
            onChooseWorld={() => dispatch({ type: 'clear-entity' })}
          />
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
          <div className="draw-menu">
            <Button
              aria-expanded={drawMenuOpen}
              aria-controls="draw-panel"
              onClick={() => setDrawMenuOpen((o) => !o)}
            >
              {`${UI.DRAW_MENU} ${drawMenuOpen ? '▴' : '▾'}`}
            </Button>
          </div>
          <CopyLinkButton />
          {drawMenuOpen && (
            <section
              id="draw-panel"
              className="draw-panel"
              aria-label={UI.DRAW_MENU_TITLE}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setDrawMenuOpen(false)
              }}
            >
              <CustomAreaPanel
                area={area}
                onChooseCustom={chooseCustom}
                polygon={{
                  onSubmit: choosePolygon,
                  drawing: polygonDrawing,
                  onToggleDrawing: () => {
                    setDrawing(false)
                    setPolygonDrawing((d) => !d)
                  },
                  cells: area.entity_type === 'CUSTOM' ? (customSeries.data?.[0]?.n_cells ?? null) : null,
                  draft: polygonDraft,
                }}
                drawing={drawing}
                onToggleDrawing={() => {
                  setPolygonDrawing(false)
                  setDrawing((d) => !d)
                }}
                customMessage={customMessage}
                customLoading={area.entity_type === 'CUSTOM' && customSeries.isFetching}
              />
            </section>
          )}
        </section>

        <StoryChips areaId={area.entity_id} month={selection.month} onChoose={chooseStory} />

        <div className="hero">
          <div className="map-column">
            <div className="map-stage">
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
                fit={mapFit}
                customBbox={area.entity_type === 'CUSTOM' ? area.bbox : null}
                customRing={area.entity_type === 'CUSTOM' ? (area.polygon ?? null) : null}
                drawing={drawing}
                onDrawn={chooseCustom}
                polygonDrawing={polygonDrawing}
                onDrawnPolygon={choosePolygon}
                anomalyOutlines={anomalyOutlines}
                loading={cells.isFetching}
                month={selection.month}
                onHoverCountry={setHoverCountry}
              />
              </Suspense>
              <MapModeSwitch mode={selectMode(drawing, polygonDrawing)} onChange={onSelectMode} drawDisabled={drawDisabled} />
              {hoverCountry !== null && !drawing && !polygonDrawing && (
                <p className="map-readout" aria-hidden="true">
                  <strong>{hoverCountry.name}</strong>
                  <span>{hoverVerdict}</span>
                </p>
              )}
            </div>
            <section aria-label="Data status" className="status">
              {(meta.isPending || ((cells.isPending || cells.isPlaceholderData) && mapAvailable)) && selection.month !== null && (
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
            <MapSourceLine methodVersion={meta.data?.method_version ?? null} />
          </div>
          <aside className="hero-side">
            <SummaryCard
              area={area}
              month={selection.month}
              status={areaSeries.isError ? 'error' : areaSeries.isPending ? 'loading' : 'ready'}
              errorMessage={summaryError}
              onRetry={summaryError === null || area.entity_type !== 'CUSTOM' ? () => void areaSeries.refetch() : undefined}
              records={areaSeries.data}
              meta={meta.data ?? null}
              headingRef={summaryHeading}
              download={<ExportButton area={area} synthetic={meta.data?.synthetic === true} />}
            />
            <TopAnomalies
              month={selection.month}
              status={anomalyStatus}
              above={countryRankings.above}
              rawOnly={rawOnly}
              onSelect={chooseAnomaly}
              onRetry={() => void anomalies.refetch()}
              onSeeAll={() => {
                setTab('anomalies')
                document.getElementById('details')?.scrollIntoView({ block: 'start' })
              }}
            />
            <section aria-label="Selection" className="selection card">
              <h2>{UI.SELECTION_TITLE}</h2>
              {selection.entity === null && <EmptyState message={UI.SELECTION_EMPTY} />}
              {selection.entity !== null && selection.entity.entity_type !== 'CELL' && (
                <p>{`Area: ${area.entity_name}${area.entity_type === 'CUSTOM' ? '' : ` (${area.entity_id})`}`}</p>
              )}
              {selectedCell !== null && <CellInfo cell={selectedCell} layer={layer} />}
            </section>
          </aside>
        </div>

        <Card id="details" className="details" aria-label={UI.TABS_LABEL}>
          <Tabs<TabId>
            idBase="details"
            label={UI.TABS_LABEL}
            value={tab}
            onChange={setTab}
            tabs={[
              {
                id: 'calendar',
                label: UI.TAB_LABELS_UI.calendar,
                panel: (
                  <CalendarPanel
                    area={area}
                    meta={meta.data ?? null}
                    selectedMonth={selection.month}
                    valueMode={rawOnly ? 'activity' : selection.valueMode}
                    source={rawOnly ? 'raw' : selection.source}
                    onValueModeChange={(valueMode) => dispatch({ type: 'set-value-mode', valueMode })}
                    onSelectMonth={(year, month) => {
                      dispatch({ type: 'set-month', year, month })
                      summaryHeading.current?.focus()
                    }}
                    onShowWorld={() => dispatch({ type: 'clear-entity' })}
                  />
                ),
              },
              {
                id: 'satellites',
                label: UI.TAB_LABELS_UI.satellites,
                panel: <WitnessPanel area={area} meta={meta.data ?? null} onShowWorld={() => dispatch({ type: 'clear-entity' })} />,
              },
              {
                id: 'evidence',
                label: UI.TAB_LABELS_UI.evidence,
                panel: (
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
                ),
              },
              {
                id: 'anomalies',
                label: UI.TAB_LABELS_UI.anomalies,
                panel: (
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
                ),
              },
            ]}
          />
        </Card>
      </main>
      )}
    </div>
    </RawOnlyContext.Provider>
  )
}
