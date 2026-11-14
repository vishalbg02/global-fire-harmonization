import { VALUE_MODE_LABELS } from '../../content/calendar.ts'
import type { ValueMode } from '../../state/selection.ts'

const MODES: readonly ValueMode[] = ['pct', 'activity']

export function ValueModeSelector({ value, onChange }: { value: ValueMode; onChange: (mode: ValueMode) => void }) {
  return (
    <fieldset className="layer-selector">
      <legend>Calendar shows</legend>
      {MODES.map((mode) => (
        <label key={mode}>
          <input
            type="radio"
            name="calendar-value-mode"
            value={mode}
            checked={value === mode}
            onChange={() => onChange(mode)}
          />
          {VALUE_MODE_LABELS[mode]}
        </label>
      ))}
    </fieldset>
  )
}
