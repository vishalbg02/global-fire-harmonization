import type { ReactNode, RefObject } from 'react'
import type { EntityMonth, Metadata } from '../../api/contract.ts'
import { ACTIONS_LABEL, PROVISIONAL_MARK, SUMMARY_ERROR, SUMMARY_LOADING } from '../../content/answer.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { StoryCaption } from '../layout/StoryCaption.tsx'
import { NOT_AVAILABLE_YET, isRawOnlyRecord, useRawOnly } from '../../content/rawOnly.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { monthLabel } from '../../state/months.ts'
import type { Area } from '../../state/selection.ts'
import { NO_DATA, verdictProbability } from '../map/format.ts'
import { EmptyState, ErrorState, Skeleton } from '../common/States.tsx'
import type { SkeletonBlock } from '../common/States.tsx'
import { HelpTip } from '../help/HelpTip.tsx'
import { Badge } from '../ui/Badge.tsx'
import { Card } from '../ui/Card.tsx'
import { IntervalBar } from './IntervalBar.tsx'
import { ReasonChips } from './ReasonChips.tsx'
import { pctParts, sentence } from './text.ts'
import { Sparkline } from './Sparkline.tsx'
import './summary.css'

export type SummaryStatus = 'loading' | 'error' | 'ready'

interface Props {
  area: Area
  month: { year: number; month: number } | null
  status: SummaryStatus
  errorMessage?: string | null
  onRetry?: () => void
  records: readonly EntityMonth[] | undefined
  meta: Metadata | null
  headingRef: RefObject<HTMLHeadingElement | null>
  /** The CSV download, the first action. */
  download: ReactNode
  /** The "Copy link" action, beside the download. */
  copyLink?: ReactNode
  /** The featured story on screen (the area and month equal it), or null. */
  story?: FeaturedStory | null
  /** Opens the Analytics details with the "Compare with" search; left out where compare is not offered. */
  onCompare?: () => void
  /** Jumps to the Details tabs below. */
  onDetails?: () => void
}

const parseYm = (ym: string) => ({ year: Number(ym.slice(0, 4)), month: Number(ym.slice(5, 7)) })

/**
 * The shape of the loaded answer (verdict, big number, probability, interval bar and its legend, sparkline, "Why" and
 * the source line), in grey, so the card keeps its height while the series loads.
 */
const SKELETON: readonly SkeletonBlock[] = [
  { h: 34, w: '46%' },
  { h: 42, w: '58%', gap: 8 },
  { h: 16, w: '74%', gap: 10 },
  { h: 24, gap: 16 },
  { h: 14, w: '86%', gap: 10 },
  { h: 14, w: '86%', gap: 6 },
  { h: 14, w: '86%', gap: 6 },
  { h: 14, w: '86%', gap: 6 },
  { h: 12, w: '62%', gap: 8 },
  { h: 78, gap: 20 },
  { h: 12, w: '92%', gap: 8 },
  { h: 12, w: '70%', gap: 4 },
  { h: 12, w: '18%', gap: 20 },
  { h: 26, w: '64%', gap: 8 },
  { h: 12, w: '96%', gap: 20 },
  { h: 12, w: '80%', gap: 4 },
]

/** The source line of the card: satellites used this month, the data level, the method, and the link to how the verdict is made. */
export function SummarySourceLine({ record, methodVersion }: { record: EntityMonth; methodVersion: string }) {
  const satellites =
    record.witnesses_used.length === 0 ? UI.SUMMARY_NO_SATELLITES : record.witnesses_used.map((w) => WITNESS_NAMES[w]).join(', ')
  const level = UI.DATA_LEVEL_TEXT[record.data_level] ?? record.data_level
  return (
    <p className="source-line">
      {`${UI.SUMMARY_SOURCE_PREFIX}; ${UI.SUMMARY_SOURCE_SATELLITES(satellites)}; ${UI.SUMMARY_SOURCE_LEVEL(level)}; ${UI.SUMMARY_METHOD(methodVersion)}. `}
      <a href={methodsHref('baseline-verdicts')}>{UI.SUMMARY_HOW_MADE}</a>
    </p>
  )
}

/** The verdict, the big % of normal, the probability sentence and the interval bar: the answer in one block. */
function Verdict({ record, areaName }: { record: EntityMonth; areaName: string }) {
  const verdict = VERDICT_PRESENTATION[record.verdict]
  const probability = verdictProbability(record)
  const pct = pctParts(record.pct_of_normal)
  return (
    <div className="verdict" data-verdict={record.verdict}>
      <div className="verdict-row">
        <Badge tone={record.verdict} icon={verdict.icon} className="summary-verdict">
          {verdict.label}
        </Badge>
        {record.verdict === 'CANNOT_DETERMINE' && <HelpTip term="cannot-determine" />}
        {record.verdict === 'NO_DETECTED_ACTIVITY' && <HelpTip term="no-detected-activity" />}
      </div>
      <p className="big num">
        {pct === null ? (
          <span className="big-none">{NO_DATA}</span>
        ) : (
          <>
            <span className="big-value">{pct.value}</span>
            <small>{pct.unit}</small>
          </>
        )}
        <HelpTip term="pct-of-normal" />
      </p>
      {probability !== null ? (
        <p className="prob">
          {`${sentence(probability)}.`}
          <HelpTip term="probability" />
        </p>
      ) : (
        // "Cannot determine" and "No detected activity" are results: their approved sentence, said plainly.
        <p className="prob prob-result">{verdict.description}</p>
      )}
      <IntervalBar record={record} areaName={areaName} />
    </div>
  )
}

/**
 * The answer for the selected area and month, in this order: the area and month, the verdict, the big % of normal,
 * the probability, the interval bar against the normal range, the sparkline, "Why", the source line and the actions.
 * Every value is the stored one for that month (nothing is computed here), and each appears once.
 */
export function SummaryCard({
  area,
  month,
  status,
  errorMessage,
  onRetry,
  records,
  meta,
  headingRef,
  download,
  copyLink,
  story = null,
  onCompare,
  onDetails,
}: Props) {
  const globalRawOnly = useRawOnly()
  const record =
    month === null ? undefined : records?.find((r) => r.year === month.year && r.month === month.month)
  const rawOnly = globalRawOnly && record !== undefined && isRawOnlyRecord(record)
  const title = month === null ? area.entity_name : `${area.entity_name}, ${monthLabel(month)}`
  const first = meta === null ? null : parseYm(meta.first_month)
  const latest = meta === null ? null : parseYm(meta.latest_month)
  const methodVersion = record?.method_version ?? meta?.method_version ?? null

  return (
    <Card className="summary" aria-label="Summary of the selected area and month" aria-busy={month !== null && status === 'loading'}>
      <p className="eyebrow">{UI.SUMMARY_EYEBROW}</p>
      <div className="summary-head">
        <h2 ref={headingRef} tabIndex={-1}>
          {title}
        </h2>
        {/* The one provisional notice of the card: it belongs to the month, so it sits beside the month. */}
        {status === 'ready' && record !== undefined && record.data_level !== 'SP' && (
          <span className="provisional-mark">
            {PROVISIONAL_MARK}
            <HelpTip term="provisional" />
          </span>
        )}
      </div>

      {month === null && <EmptyState message={UI.SUMMARY_NO_MONTH} />}
      {month !== null && status === 'loading' && <Skeleton what={SUMMARY_LOADING} blocks={SKELETON} className="summary-skeleton" />}
      {month !== null && status === 'error' && <ErrorState message={errorMessage ?? SUMMARY_ERROR} onRetry={onRetry} />}
      {month !== null && status === 'ready' && record === undefined && <EmptyState message={UI.SUMMARY_NO_RECORD(monthLabel(month))} />}

      {month !== null && status === 'ready' && record !== undefined && (
        <>
          {rawOnly ? <p className="state state-empty">{NOT_AVAILABLE_YET}</p> : <Verdict record={record} areaName={area.entity_name} />}
          {!rawOnly && records !== undefined && first !== null && latest !== null && (
            <Sparkline records={records} selected={month} first={first} latest={latest} areaName={area.entity_name} />
          )}
          {!rawOnly && <ReasonChips key={`${area.entity_id}-${record.year}-${record.month}`} codes={record.reason_codes} />}
          {methodVersion !== null && <SummarySourceLine record={record} methodVersion={methodVersion} />}
        </>
      )}
      <div className="summary-actions" role="group" aria-label={ACTIONS_LABEL}>
        {download}
        {copyLink}
        {onCompare !== undefined && (
          <button type="button" className="btn btn-secondary" onClick={onCompare}>
            {UI.COMPARE_WITH}
          </button>
        )}
        {onDetails !== undefined && (
          <button type="button" className="btn btn-secondary" onClick={onDetails} title={UI.DETAILS_JUMP_HINT}>
            {UI.DETAILS_JUMP}
          </button>
        )}
      </div>
      {story !== null && <StoryCaption story={story} />}
    </Card>
  )
}
