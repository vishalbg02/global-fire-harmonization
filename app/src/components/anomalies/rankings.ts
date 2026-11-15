import type { Anomaly } from '../../api/contract.ts'
import { formatProbability } from '../map/format.ts'

/** The world is a single entity, so it is left out of the ranking; there are two tabs. */
export type RankingTab = 'COUNTRY' | 'CONTINENT'

export const TAB_LABELS: Record<RankingTab, string> = {
  COUNTRY: 'Countries',
  CONTINENT: 'Continents',
}

export const PAGE_SIZE = 10
export const EXPANDED_SIZE = 20

export interface Rankings {
  above: Anomaly[]
  below: Anomaly[]
}

/** The stored probability that belongs to an entry's verdict. */
export function entryProbability(a: Anomaly): number | null {
  return a.verdict === 'ABOVE_NORMAL' ? a.p_above : a.p_below
}

/**
 * Splits the API's anomalies of one entity type into the two rankings the Lead asked for:
 * "most likely above normal" and "most likely below normal". The API's order is kept: the
 * API alone orders (probability, then distance from normal, then entity id; api/README.md), so
 * nothing is sorted, computed or filtered by a threshold here. The API already leaves out
 * every verdict other than above and below.
 */
export function rankAnomalies(anomalies: readonly Anomaly[], tab: RankingTab): Rankings {
  const ofType = anomalies.filter((a) => a.entity_type === tab)
  return {
    above: ofType.filter((a) => a.verdict === 'ABOVE_NORMAL'),
    below: ofType.filter((a) => a.verdict === 'BELOW_NORMAL'),
  }
}

export function topN<T>(list: readonly T[], n: number): T[] {
  return list.slice(0, n)
}

/** "82% likely above normal", "more than 99% likely ..." for >= 0.995; null when missing. */
export function probabilityText(a: Anomaly): string | null {
  const p = entryProbability(a)
  if (p === null) return null
  return `${formatProbability(p)} likely ${a.verdict === 'ABOVE_NORMAL' ? 'above' : 'below'} normal`
}

export function pctText(a: Anomaly): string {
  return a.pct_of_normal === null ? 'no data' : `${Math.round(a.pct_of_normal)}% of normal`
}

/**
 * How many areas of a type are in neither ranking. The API gives no count of the verdicts it
 * leaves out, so this is the number of areas of the type minus the ranked ones: it includes
 * "within normal" areas as well as "cannot determine" and "no detected activity" ones.
 */
export function notRankedCount(totalAreas: number, rankings: Rankings): number {
  return Math.max(0, totalAreas - rankings.above.length - rankings.below.length)
}

/** The ISO3 codes of the countries shown in the two lists, for the map outlines. */
export function outlinedCountries(shownAbove: readonly Anomaly[], shownBelow: readonly Anomaly[]): {
  above: string[]
  below: string[]
} {
  const ids = (list: readonly Anomaly[]) => list.filter((a) => a.entity_type === 'COUNTRY').map((a) => a.entity_id)
  return { above: ids(shownAbove), below: ids(shownBelow) }
}

export function entryAriaLabel(rank: number, a: Anomaly): string {
  const parts = [`Rank ${rank}`, a.entity_name, probabilityText(a) ?? 'probability not available', pctText(a)]
  return parts.join(', ')
}
