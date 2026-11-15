/**
 * Source lines for the interface (T-076, the Lead's addition on PR #74).
 *
 * Every link is in docs/DATA_SOURCES.md section 9 (verified 2026-11-15); no other URL, version or date is used. Every date and
 * version below comes from the arguments (the metadata of GET /api/meta, the record of one month), never from a literal.
 * Voice: plain, factual, no marketing words. Member 3 renders the segments; a segment with `href` is a link.
 */
import type { DataLevel, Witness } from '../api/contract.ts'
import { methodsHref } from './methodsLink.ts'
import { WITNESS_NAMES } from './witnesses.ts'

export interface TextSegment {
  readonly text: string
  /** External or in-app link; absent for plain text. */
  readonly href?: string
}

/** The links of docs/DATA_SOURCES.md section 9. */
export const SOURCE_HREF = {
  firms: 'https://www.earthdata.nasa.gov/data/tools/firms',
  firmsFaq: 'https://www.earthdata.nasa.gov/data/tools/firms/faq',
  modis: 'https://doi.org/10.5067/MODIS/MYD14.061',
  viirsSnpp: 'https://doi.org/10.5067/VIIRS/VNP14IMG.002',
  viirsNoaa20: 'https://doi.org/10.5067/VIIRS/VJ114IMG.002',
} as const

/** The part of the metadata the source lines use. `grid` and `snapshot` are optional because the typed contract does not list them. */
export interface SourceMetadata {
  method_version: string
  first_month: string
  latest_month: string
  provisional_months: readonly string[]
  grid?: { analysis_deg: number }
  data_snapshot?: { zips_downloaded?: string; api_pulled?: string }
}

/** Plain text of a list of segments. */
export const segmentsText = (segments: readonly TextSegment[]): string => segments.map((s) => s.text).join('')

/**
 * Map footer. "Data: NASA FIRMS MODIS Collection 6.1 and VIIRS 375 m (S-NPP, NOAA-20) active-fire detections; archive (SP) through
 * 2026-07, near-real-time (NRT, provisional) from 2026-08; analysis grid 0.5 degrees. Harmonized by this project, method 0.1.0."
 */
export function mapFooterSegments(meta: SourceMetadata): TextSegment[] {
  const first = meta.provisional_months[0]
  const levels: TextSegment[] =
    first === undefined
      ? [{ text: 'archive ' }, { text: '(SP)', href: SOURCE_HREF.firmsFaq }, { text: ` through ${meta.latest_month}` }]
      : [
          { text: 'archive ' },
          { text: '(SP)', href: SOURCE_HREF.firmsFaq },
          { text: ` before ${first}, near-real-time ` },
          { text: '(NRT, provisional)', href: SOURCE_HREF.firmsFaq },
          { text: ` from ${first} to ${meta.latest_month}` },
        ]
  const grid = meta.grid?.analysis_deg
  const snapshot = meta.data_snapshot
  const downloaded = snapshot?.zips_downloaded ?? snapshot?.api_pulled
  return [
    { text: 'Data: ' },
    { text: 'NASA FIRMS', href: SOURCE_HREF.firms },
    { text: ' ' },
    { text: 'MODIS Collection 6.1', href: SOURCE_HREF.modis },
    { text: ' and ' },
    { text: 'VIIRS 375 m', href: SOURCE_HREF.viirsSnpp },
    { text: ' (' },
    { text: 'S-NPP', href: SOURCE_HREF.viirsSnpp },
    { text: ', ' },
    { text: 'NOAA-20', href: SOURCE_HREF.viirsNoaa20 },
    { text: ') active-fire detections; ' },
    ...levels,
    { text: `${grid === undefined ? '' : `; analysis grid ${grid}°`}${downloaded === undefined ? '' : `; downloaded ${downloaded}`}. ` },
    { text: `Harmonized by this project, method ${meta.method_version}.` },
  ]
}

/** What each data level means, in the words of docs/DATA_SOURCES.md section 3. */
export const DATA_LEVEL_TEXT: Record<DataLevel, string> = {
  SP: 'science-quality archive (SP)',
  NRT: 'near-real-time (NRT), provisional',
  MIXED: 'archive (SP) and near-real-time (NRT) days, provisional',
}

/** The anchor of "how this verdict is made" on the methods page (section "The baseline and the five verdicts"). */
export const VERDICT_METHOD_ANCHOR = 'baseline-verdicts'

/**
 * The per-month source line for the summary card and the evidence panel: the satellites used, the data level and a link to
 * "How this verdict is made". `rawOnly` records (no harmonized values) name no satellites.
 */
export function monthSourceSegments(
  record: { witnesses_used: readonly Witness[]; data_level: DataLevel },
  location?: { pathname: string; search: string },
): TextSegment[] {
  const satellites =
    record.witnesses_used.length === 0 ? 'no satellite contributed usable data' : record.witnesses_used.map((w) => WITNESS_NAMES[w]).join(', ')
  return [
    { text: `Source: NASA FIRMS; satellites used: ${satellites}; data level: ${DATA_LEVEL_TEXT[record.data_level]}. ` },
    { text: 'How this verdict is made', href: methodsHref(VERDICT_METHOD_ANCHOR, location) },
  ]
}

/** Captions with unit and source for the charts and the calendar. */
export const CALENDAR_CAPTION_PCT =
  'Each cell is one month: the harmonized estimate as a percentage of the median of the same calendar month in 2003 to 2022 (100% is typical). Source: NASA FIRMS, harmonized by this project.'
export const CALENDAR_CAPTION_ACTIVITY =
  'Each cell is one month: the estimate in fire-active cell-days, Aqua-equivalent (a map cell counts once per day with a detection). Source: NASA FIRMS, harmonized by this project.'
export const CALENDAR_CAPTION_RAW =
  'Each cell is one month: the raw count in fire-active cell-days, not converted and not comparable between satellites. Source: NASA FIRMS.'
export const WITNESS_CHART_CAPTION =
  'Monthly fire-active cell-days: the harmonized estimate with its 90% interval (Aqua-equivalent) and the raw count of each satellite (not converted). Source: NASA FIRMS, harmonized by this project.'
