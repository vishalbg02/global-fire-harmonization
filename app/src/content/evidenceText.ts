/**
 * Two texts of the evidence panel (T-076).
 *
 * The panel used to say "Satellites disagree; uncertainty widened (disagreement scale 1.78)" and, below it, "No caveats are
 * recorded for this month". Both were true, but they read as a contradiction: the disagreement scale is applied (the interval is
 * widened) whenever it is above 1, while the caveat code WITNESS_DISAGREEMENT is stored only when it is above 2 (D-028 and T-013).
 * The note now says which of the two cases it is.
 */

/** The largest scale that is a routine widening; above it the stored reason code WITNESS_DISAGREEMENT is also listed under "Why". */
export const DISAGREEMENT_CAVEAT_ABOVE = 2

export function disagreementNote(scale: number): string {
  const head = `The satellites differ by more than their own uncertainty explains, so the uncertainty range was widened (disagreement scale ${scale.toFixed(2)}).`
  return scale > DISAGREEMENT_CAVEAT_ABOVE
    ? `${head} The difference is large enough to be listed as a caveat under "Why".`
    : `${head} This is a routine adjustment, not a caveat.`
}

export const NO_CAVEATS_TEXT = 'No caveat flags are recorded for this month.'
