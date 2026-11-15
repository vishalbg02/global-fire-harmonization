import { SOURCE_HREF } from '../../content/sources.ts'
import type { SourceMetadata, TextSegment } from '../../content/sources.ts'

/** The source line under every chart: from `sources.ts` (links of docs/DATA_SOURCES.md section 9) and the metadata, nothing typed by hand. */
export function chartSourceSegments(meta: SourceMetadata): TextSegment[] {
  const snapshot = meta.data_snapshot?.zips_downloaded ?? meta.data_snapshot?.api_pulled
  return [
    { text: 'Source: ' },
    { text: 'NASA FIRMS', href: SOURCE_HREF.firms },
    { text: ` active-fire detections, harmonized by this project, method ${meta.method_version}${snapshot === undefined ? '' : `; downloaded ${snapshot}`}. Latest month ${meta.latest_month}.` },
  ]
}

export const ANNUAL_NOTE =
  'Sum of monthly estimates; intervals not combined. Each year sums only the months that have an estimate; a hollow marker is a partial year. Raw is the unconverted count of all satellites together, so it is not comparable across satellite changes.'
export const SEASON_NOTE =
  'The normal range is the 25th to 75th percentile of the same calendar month in 2003 to 2022, as stored in the products.'
export const COVERAGE_NOTE =
  'Determinable means any verdict except "cannot determine". A country or a continent counts the cells stored for it (the country of a cell is the one FIRMS lists it under); the world counts every cell. This counts analysis cells, not land area.'
/** Shown instead of a figure when the API does not send each cell's country and continent (an older API or the offline copy; T-090). */
export const COVERAGE_AREAS_MISSING =
  "Coverage for this area needs the country and continent of each cell, which this data service or offline copy does not send. It is shown for the world only."
export const COVERAGE_NO_CELLS = 'No analysis cell is stored for this area in this month.'

// The "Compare with" search (T-090).
export const COMPARE_LABEL = 'Compare with'
export const COMPARE_PLACEHOLDER = 'Search a country or continent'
export const COMPARE_HELP = 'Optional. Type to search; arrow keys and Enter choose, Escape closes.'
export const COMPARE_NONE = 'No comparison'
export const COMPARE_CLEAR = 'Remove the comparison'
export const COMPARE_NO_MATCH = (query: string) => `No country or continent matches "${query}".`
export const COMPARE_RESULTS = (n: number) => `${n} ${n === 1 ? 'area' : 'areas'} found`
export const COMPARE_LISTS_FAILED = 'The list of countries and continents could not be loaded, so the comparison cannot be chosen.'
export const COMPARE_NOTE = 'Monthly harmonized estimate as a percentage of the median of the same calendar month in 2003 to 2022. A gap is a month with no estimate.'
