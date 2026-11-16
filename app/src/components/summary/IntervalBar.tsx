import { useId } from 'react'
import {
  BAR_ESTIMATE,
  BAR_INTERVAL,
  BAR_MEDIAN,
  BAR_NAME,
  BAR_NONE,
  BAR_NORMAL,
  BAR_TEXT,
  BAR_UNIT_LABEL,
} from '../../content/answer.ts'
import { SPARK_UNIT } from '../../content/ui.ts'
import { HelpTip } from '../help/HelpTip.tsx'
import { intervalBar, intervalValues } from './intervalBar.ts'
import { intervalTexts } from './text.ts'

const W = 320
const H = 24
const MID = H / 2

type Values = Parameters<typeof intervalValues>[0]

type SymbolKind = 'estimate' | 'interval' | 'band' | 'median'

/** The legend key: the same shape as on the bar, so the four parts differ by shape and not by colour alone. */
function Key({ kind }: { kind: SymbolKind }) {
  return (
    <svg className="ibar-key" viewBox="0 0 16 12" width="16" height="12" aria-hidden="true" focusable="false">
      {kind === 'estimate' && <circle cx="8" cy="6" r="4" className="ibar-estimate" />}
      {kind === 'interval' && <rect x="1" y="4" width="14" height="4" className="ibar-interval" />}
      {kind === 'band' && (
        <>
          <rect x="1.5" y="1.5" width="13" height="9" className="ibar-band-key" />
          <path d="M1.5 7.5 L5.5 1.5 M5.5 10.5 L11.5 1.5 M11.5 10.5 L14.5 6" className="ibar-hatch-line" />
        </>
      )}
      {kind === 'median' && <line x1="8" x2="8" y1="0.5" y2="11.5" className="ibar-median" />}
    </svg>
  )
}

/**
 * The estimate (a dot), its 90% interval (a solid bar) and the normal range (a hatched band, with the median as a
 * tick) on one line from 0, so "above normal" can be seen. Display only: the printed numbers are the stored values
 * through `oneDecimal`; the drawing positions are never printed. A missing value is not drawn and reads "no data" or
 * "not available".
 */
export function IntervalBar({ record, areaName }: { record: Values; areaName: string }) {
  const rawId = useId()
  const id = `ibar-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`
  const values = intervalValues(record)
  const geo = intervalBar(values, W)
  const text = intervalTexts(values)
  const description = BAR_TEXT({ ...text, unit: SPARK_UNIT })
  return (
    <figure className="ibar">
      {geo === null ? (
        <p className="ibar-none">{BAR_NONE}</p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="ibar-svg" role="img" aria-labelledby={`${id}-name ${id}-text`}>
          <title id={`${id}-name`}>{BAR_NAME(areaName)}</title>
          <desc id={`${id}-text`}>{description}</desc>
          <defs>
            <pattern id={`${id}-hatch`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="5" height="5" className="ibar-band-fill" />
              <line x1="0" y1="0" x2="0" y2="5" className="ibar-hatch-line" />
            </pattern>
          </defs>
          <line x1={0} x2={W} y1={MID} y2={MID} className="ibar-track" />
          <line x1={geo.origin} x2={geo.origin} y1={MID - 4} y2={MID + 4} className="ibar-origin" />
          {geo.band !== null && (
            <rect x={geo.band.x} y={2} width={geo.band.w} height={H - 4} fill={`url(#${id}-hatch)`} className="ibar-band" />
          )}
          {geo.median !== null && <line x1={geo.median} x2={geo.median} y1={0.5} y2={H - 0.5} className="ibar-median" />}
          {geo.interval !== null && (
            <rect x={geo.interval.x} y={MID - 3} width={geo.interval.w} height={6} className="ibar-interval" />
          )}
          {geo.estimate !== null && <circle cx={geo.estimate} cy={MID} r={5} className="ibar-estimate" />}
        </svg>
      )}
      <dl className="ibar-legend">
        <div>
          <dt>
            <Key kind="estimate" />
            {BAR_ESTIMATE}
          </dt>
          <dd className="num">{text.estimate}</dd>
        </div>
        <div>
          <dt>
            <Key kind="interval" />
            {BAR_INTERVAL}
            <HelpTip term="interval-90" />
          </dt>
          <dd className="num">{text.interval}</dd>
        </div>
        <div>
          <dt>
            <Key kind="band" />
            {BAR_NORMAL}
            <HelpTip term="normal-range" />
          </dt>
          <dd className="num">{text.normal}</dd>
        </div>
        <div>
          <dt>
            <Key kind="median" />
            {BAR_MEDIAN}
          </dt>
          <dd className="num">{text.median}</dd>
        </div>
      </dl>
      <p className="ibar-unit">
        {`${BAR_UNIT_LABEL}: ${SPARK_UNIT}`}
        <HelpTip term="cell-days" />
      </p>
    </figure>
  )
}
