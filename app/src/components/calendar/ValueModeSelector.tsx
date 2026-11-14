import { useRawOnly } from '../../content/rawOnly.ts'
import { VALUE_MODE_LABELS } from '../../content/calendar.ts'
import type { ValueMode } from '../../state/selection.ts'

const MODES: readonly ValueMode[] = ['pct', 'activity']

interface Props {
  value: ValueMode
  onChange: (mode: ValueMode) => void
  /** No baseline in the shown series, so "% of normal" cannot be chosen. Defaults to the global raw-only state. */
  pctUnavailable?: boolean
  /** The shown series is raw-only (changes the wording of the note). Defaults to the global state. */
  rawOnly?: boolean
}

export function ValueModeSelector({ value, onChange, pctUnavailable, rawOnly }: Props) {
  // % of normal needs a baseline: not available while only raw data exist, or until verdicts are computed.
  const globalRawOnly = useRawOnly()
  const unavailable = pctUnavailable ?? globalRawOnly
  const rawOnlyNote = rawOnly ?? globalRawOnly
  return (
    <fieldset className="layer-selector">
      <legend>Calendar shows</legend>
      {MODES.map((mode) => (
        <label key={mode} className={mode === 'pct' && unavailable ? 'is-disabled' : undefined}>
          <input
            type="radio"
            name="calendar-value-mode"
            value={mode}
            checked={value === mode}
            aria-disabled={(mode === 'pct' && unavailable) || undefined}
            onChange={() => {
              if (!(mode === 'pct' && unavailable)) onChange(mode)
            }}
          />
          {VALUE_MODE_LABELS[mode]}
        </label>
      ))}
      {unavailable && (
        <p className="source-note">
          {rawOnlyNote
            ? '% of normal is not available yet (raw data only).'
            : '% of normal is not available yet (no baseline until the verdicts are computed).'}
        </p>
      )}
    </fieldset>
  )
}
