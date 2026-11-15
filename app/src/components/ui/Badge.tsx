import type { HTMLAttributes } from 'react'
import type { Verdict } from '../../api/contract.ts'

export type BadgeTone = Verdict | 'neutral' | 'warn'

interface Props extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** A glyph shown before the label, hidden from screen readers (the label says it). */
  icon?: string
}

const TONE_CLASS: Record<BadgeTone, string> = {
  ABOVE_NORMAL: 'badge-above',
  BELOW_NORMAL: 'badge-below',
  WITHIN_NORMAL: 'badge-within',
  CANNOT_DETERMINE: 'badge-cannot',
  NO_DETECTED_ACTIVITY: 'badge-none',
  neutral: 'badge-neutral',
  warn: 'badge-warn',
}

/** A status badge. The verdict tones always carry the verdict icon and label, so colour is never the only cue. */
export function Badge({ tone = 'neutral', icon, className, children, ...rest }: Props) {
  return (
    <span className={`ui-badge ${TONE_CLASS[tone]}${className === undefined ? '' : ` ${className}`}`} {...rest}>
      {icon !== undefined && (
        <span className="ui-badge-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  )
}
