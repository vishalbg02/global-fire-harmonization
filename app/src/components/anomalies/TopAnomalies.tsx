import type { Anomaly } from '../../api/contract.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { monthLabel } from '../../state/months.ts'
import { ErrorState, LoadingState } from '../common/States.tsx'
import { Card } from '../ui/Card.tsx'
import { entryAriaLabel, pctText } from './rankings.ts'
import type { AnomalyStatus } from './AnomalyPanel.tsx'

export const TOP_COUNT = 5

interface Props {
  month: { year: number; month: number } | null
  status: AnomalyStatus
  /** The countries most likely above normal, in the API's order. */
  above: readonly Anomaly[]
  rawOnly: boolean
  onSelect: (a: Anomaly) => void
  onSeeAll: () => void
  onRetry: () => void
}

/** The five countries most likely above normal this month; the full ranking is in the "All anomalies" tab. */
export function TopAnomalies({ month, status, above, rawOnly, onSelect, onSeeAll, onRetry }: Props) {
  const shown = above.slice(0, TOP_COUNT)
  return (
    <Card className="top-anomalies" aria-label="Biggest anomalies">
      <h3>{month === null ? 'Biggest anomalies' : UI.TOP_ANOMALIES_TITLE(monthLabel(month))}</h3>
      {status === 'loading' && <LoadingState what="the anomalies" />}
      {status === 'error' && !rawOnly && <ErrorState message="Data are not available right now. The anomaly list could not be loaded." onRetry={onRetry} />}
      {status === 'ready' && !rawOnly && shown.length === 0 && <p className="state state-empty">{UI.TOP_ANOMALIES_NONE}</p>}
      {status === 'ready' && !rawOnly && shown.length > 0 && (
        <ol>
          {shown.map((a, i) => (
            <li key={a.entity_id}>
              <button type="button" aria-label={entryAriaLabel(i + 1, a)} onClick={() => onSelect(a)}>
                <span aria-hidden="true">{`${a.entity_name} ${VERDICT_PRESENTATION[a.verdict].icon}`}</span>
                <span aria-hidden="true" className="num top-pct">
                  {pctText(a)}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
      <button type="button" className="link-button" onClick={onSeeAll}>
        {UI.TOP_ANOMALIES_ALL}
      </button>
    </Card>
  )
}
