import { useRawOnly } from '../../content/rawOnly.ts'
import { VALUE_MODE_LABELS } from '../../content/calendar.ts'
import type { ValueMode } from '../../state/selection.ts'

const MODES: readonly ValueMode[] = ['pct', 'activity']

export function ValueModeSelector({ value, onChange }: { value: ValueMode; onChange: (mode: ValueMode) => void }) {
  // % of normal needs a baseline: not available while only raw data exist.
  const rawOnly = useRawOnly()
  return (
    <fieldset className="layer-selector">
      <legend>Calendar shows</legend>
      {MODES.map((mode) => (
        <label key={mode} className={mode === 'pct' && rawOnly ? 'is-disabled' : undefined}>
          <input
            type="radio"
            name="calendar-value-mode"
            value={mode}
            checked={value === mode}
            aria-disabled={(mode === 'pct' && rawOnly) || undefined}
            onChange={() => {
              if (!(mode === 'pct' && rawOnly)) onChange(mode)
            }}
          />
          {VALUE_MODE_LABELS[mode]}
        </label>
      ))}
    {rawOnly && <p className="source-note">% of normal is not available yet (raw data only).</p>}
    </fieldset>
  )
}
