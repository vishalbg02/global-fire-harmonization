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
  'Determinable means any verdict except "cannot determine". All analysis cells of the world are counted. This counts analysis cells, not land area.'
/** Shown instead of a figure for a country or a continent (Lead's decision on PR #85): a bounding box would count neighbouring areas' cells. */
export const COVERAGE_WORLD_ONLY = 'Coverage for this area needs the cell-to-country link; shown for the world only.'
export const COMPARE_NOTE = 'Monthly harmonized estimate as a percentage of the median of the same calendar month in 2003 to 2022. A gap is a month with no estimate.'
