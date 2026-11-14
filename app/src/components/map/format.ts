import type { MapCell } from '../../api/contract.ts'

export const NO_DATA = 'no data'

/** Whole-number percentage of a 0-1 probability, or null. */
export function wholePercent(p: number | null): number | null {
  return p === null ? null : Math.round(p * 100)
}

export function formatPctOfNormal(v: number | null): string {
  return v === null ? NO_DATA : `${Math.round(v)}% of normal`
}

function oneDecimal(v: number): string {
  return v.toFixed(1)
}

/** "12.3 (90% interval 8.1 to 16.4)"; null estimate is "no data", never 0. */
export function formatEstimate(cell: MapCell): string {
  if (cell.estimate === null) return NO_DATA
  if (cell.ci90_low === null || cell.ci90_high === null) {
    return `${oneDecimal(cell.estimate)} (interval not available)`
  }
  return `${oneDecimal(cell.estimate)} (90% interval ${oneDecimal(cell.ci90_low)} to ${oneDecimal(cell.ci90_high)})`
}

/** "82% likely above normal" for confident verdicts; null for the others. */
export function verdictProbability(cell: MapCell): string | null {
  const wording: Partial<Record<MapCell['verdict'], [number | null, string]>> = {
    ABOVE_NORMAL: [cell.p_above, 'above normal'],
    BELOW_NORMAL: [cell.p_below, 'below normal'],
    WITHIN_NORMAL: [cell.p_within, 'within normal'],
  }
  const entry = wording[cell.verdict]
  if (entry === undefined) return null
  const pct = wholePercent(entry[0])
  return pct === null ? null : `${pct}% likely ${entry[1]}`
}
