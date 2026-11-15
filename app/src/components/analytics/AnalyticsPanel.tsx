import { useEffect, useMemo, useState } from 'react'
import { fetchCellAreas, fetchEntities, fetchMapCells, fetchMeta, fetchSeries } from '../../api/client.ts'
import type { SeriesEntityType } from '../../api/client.ts'
import type { EntityItem, EntityMonth, MapCell, Metadata } from '../../api/contract.ts'
import type { CellAreas } from '../../api/mapColumns.ts'
import type { SourceMetadata, TextSegment } from '../../content/sources.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import './analytics.css'
import { AnalyticsChart } from './AnalyticsChart.tsx'
import { annualOption, compareOption, seasonOption, wholeNumber } from './chartOptions.ts'
import { MONTH_NAMES, annualSeries, compareSeries, coverage, coverageInArea, rankInMonth, rankText, seasonProfile } from './compute.ts'
import type { Box } from './compute.ts'
import { CompareSearch } from './CompareSearch.tsx'
import type { CompareChoice } from './CompareSearch.tsx'
import { ANNUAL_NOTE, COMPARE_CLEAR, COMPARE_NOTE, COVERAGE_AREAS_MISSING, COVERAGE_NOTE, COVERAGE_NO_CELLS, SEASON_NOTE, chartSourceSegments } from './text.ts'

/** A preset area (the series endpoint serves countries, continents and the world). `bbox` is accepted for compatibility and is not used: coverage counts the cells stored for the area (T-090). */
export interface AnalyticsArea {
  entityType: SeriesEntityType
  entityId: string
  name: string
  bbox?: Box | null
}

/**
 * Props agreed with Member 3 on PR #78. The panel fetches through the app's API client only. `cells` is optional: pass the cells of the
 * selected month (layer verdict) from the map's own cache to avoid a second download; without it the panel fetches them.
 */
export interface AnalyticsPanelProps {
  area: AnalyticsArea
  compareArea?: AnalyticsArea | null
  /** Called when the user chooses or removes the comparison in the panel's own search (the app keeps it in the link as `compare=`). */
  onCompareChange?: (area: AnalyticsArea | null) => void
  year: number
  month: number
  cells?: readonly MapCell[]
  meta?: SourceMetadata
}

type Load<T> = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; value: T }

function useLoad<T>(load: () => Promise<T>, deps: readonly unknown[]): Load<T> {
  const [state, setState] = useState<Load<T>>({ status: 'loading' })
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    let alive = true
    setState({ status: 'loading' })
    load().then(
      (value) => alive && setState({ status: 'ready', value }),
      (e: unknown) => alive && setState({ status: 'error', message: e instanceof Error ? e.message : 'The data could not be loaded.' }),
    )
    return () => {
      alive = false
    }
  // The caller lists the dependencies of `load` explicitly.
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

function Segments({ segments }: { segments: readonly TextSegment[] }) {
  return (
    <>
      {segments.map((s, i) =>
        s.href === undefined ? (
          <span key={i}>{s.text}</span>
        ) : (
          <a key={i} href={s.href} target="_blank" rel="noreferrer">
            {s.text}
          </a>
        ),
      )}
    </>
  )
}

function Status({ state, what }: { state: Load<unknown>; what: string }) {
  if (state.status === 'loading') return <p className="analytics-status">Loading {what}…</p>
  if (state.status === 'error') return <p className="analytics-error" role="alert">{what}: {state.message}</p>
  return null
}

/** The analytics of one area and month: five views from the stored values (T-083). */
export function AnalyticsPanel({ area, compareArea = null, onCompareChange, year, month, cells, meta }: AnalyticsPanelProps) {
  // The comparison is the app's (the link) when it controls it, and the panel's own otherwise.
  const [chosen, setChosen] = useState<AnalyticsArea | null>(compareArea)
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setChosen(compareArea), [compareArea?.entityType, compareArea?.entityId, compareArea?.name])
  const lists = useLoad<{ countries: EntityItem[]; continents: EntityItem[] }>(
    async () => ({ countries: await fetchEntities('COUNTRY'), continents: await fetchEntities('CONTINENT') }),
    [],
  )
  const listed = lists.status === 'ready' ? lists.value : null
  const nameOf = (a: AnalyticsArea): string => {
    const list = a.entityType === 'COUNTRY' ? listed?.countries : a.entityType === 'CONTINENT' ? listed?.continents : undefined
    return list?.find((e) => e.entity_id === a.entityId)?.entity_name ?? a.name
  }
  const same = chosen !== null && chosen.entityType === area.entityType && chosen.entityId === area.entityId
  const shownCompare = chosen === null || same ? null : { ...chosen, name: nameOf(chosen) }
  const choose = (next: CompareChoice | null) => {
    const picked = next === null ? null : { entityType: next.entityType, entityId: next.entityId, name: next.name }
    setChosen(picked)
    onCompareChange?.(picked)
  }
  const series = useLoad<EntityMonth[]>(() => fetchSeries(area.entityType, area.entityId), [area.entityType, area.entityId])
  const other = useLoad<EntityMonth[] | null>(
    () => (shownCompare === null ? Promise.resolve(null) : fetchSeries(shownCompare.entityType, shownCompare.entityId)),
    [shownCompare?.entityType, shownCompare?.entityId],
  )
  // Coverage: the world counts every cell; a country or a continent counts the cells stored for it (T-090), which needs the
  // country and continent of each cell from the API. Without them the panel says so and shows no figure.
  const isWorld = area.entityType === 'GLOBAL'
  const areas = useLoad<CellAreas | null>(() => (isWorld ? Promise.resolve(null) : fetchCellAreas()), [isWorld])
  const metadata = useLoad<Metadata | SourceMetadata>(() => (meta === undefined ? fetchMeta() : Promise.resolve(meta)), [meta])
  const mapCells = useLoad<readonly MapCell[]>(
    () => (cells === undefined ? fetchMapCells(year, month, 'verdict') : Promise.resolve(cells)),
    [cells, year, month],
  )

  const records = series.status === 'ready' ? series.value : null
  const annual = useMemo(() => (records === null ? null : annualSeries(records)), [records])
  const season = useMemo(() => (records === null ? null : seasonProfile(records, year)), [records, year])
  const rank = useMemo(() => (records === null ? null : rankInMonth(records, year, month)), [records, year, month])
  const cover = useMemo(() => {
    if (mapCells.status !== 'ready') return null
    if (isWorld) return coverage(mapCells.value, null)
    if (areas.status !== 'ready' || areas.value === null || area.entityType === 'GLOBAL') return null
    return coverageInArea(mapCells.value, areas.value, area.entityType, area.entityId)
  }, [mapCells, areas, isWorld, area.entityType, area.entityId])
  const areasMissing = !isWorld && areas.status === 'ready' && areas.value === null
  const compare = useMemo(
    () => (records !== null && other.status === 'ready' && other.value !== null ? compareSeries(records, other.value) : null),
    [records, other],
  )
  const source = metadata.status === 'ready' ? <p className="analytics-source"><Segments segments={chartSourceSegments(metadata.value)} /></p> : null
  const monthName = MONTH_NAMES[month - 1]

  return (
    <div className="analytics" aria-label={`Analytics for ${area.name}, ${monthName} ${year}`}>
      <section aria-labelledby="an-annual">
        <h3 id="an-annual">Raw against harmonized, by year</h3>
        <p className="analytics-lede">The raw count steps up where a satellite joins; the harmonized estimate is built to stay on one scale.</p>
        <Status state={series} what="the series" />
        {annual !== null && (
          <>
            <AnalyticsChart option={annualOption(annual)} label={`Annual sums of raw and harmonized fire-active cell-days for ${area.name}, with the satellite joins in 2012 and 2018 marked. The table gives the same values.`} />
            <p className="analytics-note">{ANNUAL_NOTE}</p>
            <details>
              <summary>Table of annual sums</summary>
              <table>
                <thead>
                  <tr><th scope="col">Year</th><th scope="col">Months</th><th scope="col">Raw</th><th scope="col">Harmonized</th></tr>
                </thead>
                <tbody>
                  {annual.map((p) => (
                    <tr key={p.year}>
                      <td>{p.year}{p.partial ? ' (partial)' : ''}</td><td>{p.monthsUsed}</td><td>{wholeNumber(p.rawSum)}</td><td>{wholeNumber(p.harmonizedSum)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
            {source}
          </>
        )}
      </section>

      <section aria-labelledby="an-season">
        <h3 id="an-season">Season profile, {year}</h3>
        {season !== null && (
          <>
            <AnalyticsChart option={seasonOption(season, year)} label={`Monthly harmonized estimate of ${year} for ${area.name} against the normal range of each calendar month. The table gives the same values.`} />
            <p className="analytics-note">{SEASON_NOTE}</p>
            <details>
              <summary>Table of the season profile</summary>
              <table>
                <thead>
                  <tr><th scope="col">Month</th><th scope="col">25th</th><th scope="col">Median</th><th scope="col">75th</th><th scope="col">{year}</th></tr>
                </thead>
                <tbody>
                  {season.map((p) => (
                    <tr key={p.month}>
                      <td>{MONTH_NAMES[p.month - 1]}</td>
                      {[p.p25, p.median, p.p75, p.selected].map((v, i) => <td key={i}>{v === null ? 'no data' : wholeNumber(v)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
            {source}
          </>
        )}
      </section>

      <section aria-labelledby="an-rank">
        <h3 id="an-rank">Rank in the record</h3>
        {records !== null && rank === null && <p className="analytics-lede">No estimate for {monthName} {year}, so there is no rank.</p>}
        {rank !== null && (
          <>
            {rankText(rank).map((line, i) => (i === 0 ? <p key={i} className="analytics-rank">{line}</p> : <p key={i} className="analytics-note">{line}</p>))}
            <p className="analytics-note">Rank among the stored harmonized estimates of the same calendar month, highest first; equal estimates share a rank.</p>
          </>
        )}
      </section>

      <section aria-labelledby="an-coverage">
        <h3 id="an-coverage">Coverage, {monthName} {year}</h3>
        <Status state={mapCells} what="the cells" />
        {!isWorld && <Status state={areas} what="the cell areas" />}
        {areasMissing && <p className="analytics-lede">{COVERAGE_AREAS_MISSING}</p>}
        {!areasMissing && mapCells.status === 'ready' && (isWorld || areas.status === 'ready') && cover === null && (
          <p className="analytics-lede">{COVERAGE_NO_CELLS}</p>
        )}
        {cover !== null && (
          <>
            <p className="analytics-coverage">{Math.round(cover.share * 100)}% of {wholeNumber(cover.cells)} cells have a determinable verdict</p>
            <ul>
              {Object.entries(cover.byVerdict)
                .sort((a, b) => b[1] - a[1])
                .map(([verdict, n]) => (
                  <li key={verdict}>{VERDICT_PRESENTATION[verdict as keyof typeof VERDICT_PRESENTATION]?.label ?? verdict}: {wholeNumber(n)}</li>
                ))}
            </ul>
            <p className="analytics-note">{COVERAGE_NOTE}</p>
          </>
        )}
      </section>

      <section aria-labelledby="an-compare">
        <h3 id="an-compare">{shownCompare === null ? 'Compare with another area' : `${area.name} compared with ${shownCompare.name}`}</h3>
        <CompareSearch
          countries={listed?.countries}
          continents={listed?.continents}
          listsFailed={lists.status === 'error'}
          value={shownCompare === null ? '' : shownCompare.name}
          onChoose={choose}
        />
        {shownCompare !== null && (
          <button type="button" className="btn analytics-compare-clear" onClick={() => choose(null)}>
            {COMPARE_CLEAR}
          </button>
        )}
        {shownCompare !== null && (
          <>
            <Status state={other} what="the second series" />
            {compare !== null && (
              <>
                <AnalyticsChart
                  option={compareOption(compare, area.name, shownCompare.name)}
                  label={`Monthly % of normal of ${area.name} and ${shownCompare.name}.`}
                />
                <p className="analytics-note">{COMPARE_NOTE}</p>
                {source}
              </>
            )}
          </>
        )}
      </section>
    </div>
  )
}
