import type { Anomaly } from '../../api/contract.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { monthLabel } from '../../state/months.ts'
import { NOT_AVAILABLE_YET, useRawOnly } from '../../content/rawOnly.ts'
import { ErrorState, LoadingState } from '../common/States.tsx'
import { PROVISIONAL_NOTICE } from '../evidence/EvidenceBody.tsx'
import {
  EXPANDED_SIZE,
  PAGE_SIZE,
  TAB_LABELS,
  entryAriaLabel,
  notRankedCount,
  pctText,
  probabilityText,
  topN,
} from './rankings.ts'
import type { RankingTab, Rankings } from './rankings.ts'

export const EMPTY_MESSAGE = 'No areas with a confident above- or below-normal verdict this month.'
export const ABOVE_HEADING = 'Most likely above normal'
export const BELOW_HEADING = 'Most likely below normal'

const TABS: readonly RankingTab[] = ['COUNTRY', 'CONTINENT']

export type AnomalyStatus = 'idle' | 'loading' | 'error' | 'ready'

interface Props {
  month: { year: number; month: number } | null
  /** True if the selected month is in the metadata's provisional months. */
  provisional: boolean
  status: AnomalyStatus
  onRetry: () => void
  tab: RankingTab
  onTabChange: (tab: RankingTab) => void
  expanded: boolean
  onToggleExpanded: () => void
  rankings: Rankings
  /** How many areas of the selected type exist in the data; null if the list is not loaded. */
  totalAreas: number | null
  onSelect: (anomaly: Anomaly) => void
}

function Entry({ rank, anomaly, onSelect }: { rank: number; anomaly: Anomaly; onSelect: (a: Anomaly) => void }) {
  const verdict = VERDICT_PRESENTATION[anomaly.verdict]
  return (
    <li>
      <button type="button" className="anomaly-entry" aria-label={entryAriaLabel(rank, anomaly)} onClick={() => onSelect(anomaly)}>
        <span className="anomaly-rank" aria-hidden="true">{`${rank}.`}</span>
        <span className="anomaly-name" aria-hidden="true">{anomaly.entity_name}</span>
        <span className="anomaly-detail" aria-hidden="true">
          {[`${verdict.icon} ${verdict.label}`, probabilityText(anomaly), pctText(anomaly)]
            .filter((part): part is string => part !== null)
            .join(', ')}
        </span>
      </button>
    </li>
  )
}

function Ranking({
  heading,
  list,
  shown,
  onSelect,
}: {
  heading: string
  list: readonly Anomaly[]
  shown: number
  onSelect: (a: Anomaly) => void
}) {
  return (
    <section className="anomaly-ranking" aria-label={heading}>
      <h3>{heading}</h3>
      {list.length === 0 ? (
        <p className="legend-note">None this month.</p>
      ) : (
        <ol>
          {topN(list, shown).map((a, i) => (
            <Entry key={`${a.entity_type}-${a.entity_id}`} rank={i + 1} anomaly={a} onSelect={onSelect} />
          ))}
        </ol>
      )}
    </section>
  )
}

/** The global anomaly overview (T-040): two rankings for the selected month, by area type. */
export function AnomalyPanel({
  month,
  provisional,
  status,
  onRetry,
  tab,
  onTabChange,
  expanded,
  onToggleExpanded,
  rankings,
  totalAreas,
  onSelect,
}: Props) {
  const shown = expanded ? EXPANDED_SIZE : PAGE_SIZE
  const rawOnly = useRawOnly()
  const longest = Math.max(rankings.above.length, rankings.below.length)
  const unranked = totalAreas === null ? null : notRankedCount(totalAreas, rankings)
  const noneAtAll = rankings.above.length === 0 && rankings.below.length === 0

  return (
    <section className="anomaly-panel" aria-label="Global anomalies">
      <h2>{month === null ? 'Anomalies' : `Anomalies in ${monthLabel(month)}`}</h2>
      {provisional && <p className="evidence-provisional">{PROVISIONAL_NOTICE}</p>}

      <div role="tablist" aria-label="Area type" className="anomaly-tabs">
        {TABS.map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => onTabChange(t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {status === 'idle' && <p className="state state-empty">Choose a month to see the anomalies.</p>}
      {status === 'loading' && <LoadingState what="the anomalies" />}
      {(status === 'error' || status === 'ready') && rawOnly && <p className="state state-empty">{NOT_AVAILABLE_YET}</p>}
      {status === 'error' && !rawOnly && (
        <ErrorState message="Data are not available right now. The anomaly list could not be loaded." onRetry={onRetry} />
      )}
      {status === 'ready' && !rawOnly && (
        <div role="tabpanel">
          {noneAtAll ? (
            <p className="state state-empty">{EMPTY_MESSAGE}</p>
          ) : (
            <>
              <Ranking heading={ABOVE_HEADING} list={rankings.above} shown={shown} onSelect={onSelect} />
              <Ranking heading={BELOW_HEADING} list={rankings.below} shown={shown} onSelect={onSelect} />
              {longest > PAGE_SIZE && (
                <button type="button" onClick={onToggleExpanded}>
                  {expanded ? 'Show fewer' : 'Show more'}
                </button>
              )}
            </>
          )}
          {unranked !== null && (
            <p className="legend-note">
              {`${unranked} of ${totalAreas} ${TAB_LABELS[tab].toLowerCase()} are in neither ranking: their verdict is within normal, cannot be determined, or no activity was detected.`}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
