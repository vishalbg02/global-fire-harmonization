import type { HarmonizedFields } from '../../api/contract.ts'

export const NO_DATA = 'no data'

export const PROBABILITY_HIGH = 'more than 99%'
export const PROBABILITY_LOW = 'less than 1%'

/**
 * A 0-1 probability as text, display only (the stored value is unchanged): a whole percentage,
 * but never "100%" or "0%": 0.995 or more reads "more than 99%", 0.005 or less "less than 1%".
 */
export function formatProbability(p: number): string {
  if (p >= 0.995) return PROBABILITY_HIGH
  if (p <= 0.005) return PROBABILITY_LOW
  return `${Math.round(p * 100)}%`
}

export function formatPctOfNormal(v: number | null): string {
  return v === null ? NO_DATA : `${Math.round(v)}% of normal`
}

function oneDecimal(v: number): string {
  return v.toFixed(1)
}

/** "12.3 (90% interval 8.1 to 16.4)"; null estimate is "no data", never 0. */
export function formatEstimate(
  cell: Pick<HarmonizedFields, 'estimate' | 'ci90_low' | 'ci90_high'>,
): string {
  if (cell.estimate === null) return NO_DATA
  if (cell.ci90_low === null || cell.ci90_high === null) {
    return `${oneDecimal(cell.estimate)} (interval not available)`
  }
  return `${oneDecimal(cell.estimate)} (90% interval ${oneDecimal(cell.ci90_low)} to ${oneDecimal(cell.ci90_high)})`
}

/** "82% likely above normal" for confident verdicts; null for the others. */
export function verdictProbability(
  cell: Pick<HarmonizedFields, 'verdict' | 'p_above' | 'p_below' | 'p_within'>,
): string | null {
  const wording: Partial<Record<HarmonizedFields['verdict'], [number | null, string]>> = {
    ABOVE_NORMAL: [cell.p_above, 'above normal'],
    BELOW_NORMAL: [cell.p_below, 'below normal'],
    WITHIN_NORMAL: [cell.p_within, 'within normal'],
  }
  const entry = wording[cell.verdict]
  if (entry === undefined) return null
  return entry[0] === null ? null : `${formatProbability(entry[0])} likely ${entry[1]}`
}
