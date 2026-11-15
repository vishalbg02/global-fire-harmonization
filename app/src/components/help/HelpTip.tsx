import { EXPLAINERS } from '../../content/help.ts'
import type { ExplainerId } from '../../content/help.ts'

/**
 * A small "?" next to a term: opens one or two sentences from the approved plain-language texts, with a link to the
 * methods page. Placed where the term appears (the answer panel, the dock, the timeline, the legend).
 */
export function HelpTip({ term }: { term: ExplainerId }) {
  const entry = EXPLAINERS[term]
  return (
    <button type="button" className="bare help-tip" aria-label={`What is ${entry.term}?`} title={entry.text}>
      ?
    </button>
  )
}
