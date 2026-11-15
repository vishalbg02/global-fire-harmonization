import type { ReactNode, RefObject } from 'react'
import type { EntityMonth, Metadata } from '../../api/contract.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { StoryCaption } from '../layout/StoryCaption.tsx'
import { NOT_AVAILABLE_YET, isRawOnlyRecord, useRawOnly } from '../../content/rawOnly.ts'
import { methodsHref, reasonAnchor } from '../../content/methodsLink.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { monthLabel } from '../../state/months.ts'
import type { Area } from '../../state/selection.ts'
import { NO_CAVEATS_TEXT } from '../../content/evidenceText.ts'
import { PROVISIONAL_NOTICE } from '../evidence/EvidenceBody.tsx'
import { NO_DATA, oneDecimal, verdictProbability } from '../map/format.ts'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { Badge } from '../ui/Badge.tsx'
import { Card } from '../ui/Card.tsx'
import { sentence } from './text.ts'
import { Sparkline } from './Sparkline.tsx'

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
  /** The CSV download, shown at the foot of the card. */
  download: ReactNode
  /** The "Copy link" action, shown beside the download. */
  copyLink?: ReactNode
  /** The featured story on screen (the area and month equal it), or null. */
  story?: FeaturedStory | null
  /** Opens the Analytics details with the "Compare with" search; left out where compare is not offered. */
  onCompare?: () => void
  /** Jumps to the Details tabs below. */
  onDetails?: () => void
}

const parseYm = (ym: string) => ({ year: Number(ym.slice(0, 4)), month: Number(ym.slice(5, 7)) })


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

/**
 * The summary of the selected area and month, always visible: the verdict first. Every value is
 * the stored one for that month (nothing is computed here).
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
  const verdict = record === undefined ? null : VERDICT_PRESENTATION[record.verdict]
  const probability = record === undefined ? null : verdictProbability(record)
  const pct = record?.pct_of_normal ?? null
  const title = month === null ? area.entity_name : `${area.entity_name}, ${monthLabel(month)}`
  const first = meta === null ? null : parseYm(meta.first_month)
  const latest = meta === null ? null : parseYm(meta.latest_month)
  const methodVersion = record?.method_version ?? meta?.method_version ?? null

  return (
    <Card className="summary" aria-label="Summary of the selected area and month">
      <p className="eyebrow">{UI.SUMMARY_EYEBROW}</p>
      <h2 ref={headingRef} tabIndex={-1}>
        {title}
      </h2>

      {month === null && <EmptyState message={UI.SUMMARY_NO_MONTH} />}
      {month !== null && status === 'loading' && <LoadingState what="the summary" />}
      {month !== null && status === 'error' && (
        <ErrorState message={errorMessage ?? 'Data are not available right now. The summary could not be loaded.'} onRetry={onRetry} />
      )}
      {month !== null && status === 'ready' && record === undefined && <EmptyState message={UI.SUMMARY_NO_RECORD(monthLabel(month))} />}

      {month !== null && status === 'ready' && record !== undefined && verdict !== null && (
        <>
          {rawOnly ? (
            <p className="state state-empty">{NOT_AVAILABLE_YET}</p>
          ) : (
            <>
              <Badge tone={record.verdict} icon={verdict.icon} className="summary-verdict">
                {verdict.label}
              </Badge>
              {probability !== null && <p className="prob">{`${sentence(probability)}.`}</p>}
              <p className="big num">
                {pct === null ? (
                  <span className="big-none">{NO_DATA}</span>
                ) : (
                  <>
                    {Math.round(pct)}
                    <small>% of normal</small>
                  </>
                )}
              </p>
            </>
          )}
          <dl className="kv">
            <dt>{UI.SUMMARY_ESTIMATE}</dt>
            <dd className="num">
              {record.estimate === null ? (rawOnly ? NOT_AVAILABLE_YET : NO_DATA) : oneDecimal(record.estimate)}
              {record.estimate !== null && <span className="kv-unit">{` ${UI.SPARK_UNIT}`}</span>}
            </dd>
            <dt>{UI.SUMMARY_INTERVAL}</dt>
            <dd className="num">
              {record.ci90_low === null || record.ci90_high === null
                ? NO_DATA
                : `${oneDecimal(record.ci90_low)} to ${oneDecimal(record.ci90_high)}`}
            </dd>
            {!rawOnly && (
              <>
                <dt>{UI.SUMMARY_SATELLITES}</dt>
                <dd>
                  {record.witnesses_used.length === 0
                    ? UI.SUMMARY_NO_SATELLITES
                    : record.witnesses_used.map((w) => WITNESS_NAMES[w]).join(', ')}
                </dd>
              </>
            )}
          </dl>
          {record.data_level !== 'SP' && <p className="evidence-provisional">{PROVISIONAL_NOTICE}</p>}
          {!rawOnly && (
            <div className="reason">
              {record.reason_codes.length === 0 ? (
                <p>{NO_CAVEATS_TEXT}</p>
              ) : (
                <ul>
                  {record.reason_codes.map((code) => (
                    <li key={code}>
                      {REASON_TEXTS[code]}{' '}
                      <a className="learn-more" href={methodsHref(reasonAnchor(code))}>
                        {UI.SUMMARY_LEARN_MORE}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {!rawOnly && records !== undefined && first !== null && latest !== null && (
            <Sparkline records={records} selected={month} first={first} latest={latest} areaName={area.entity_name} />
          )}
          {methodVersion !== null && <SummarySourceLine record={record} methodVersion={methodVersion} />}
        </>
      )}
      {story !== null && <StoryCaption story={story} />}
      <div className="summary-download">{download}</div>
      <div className="summary-actions">
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
    </Card>
  )
}

