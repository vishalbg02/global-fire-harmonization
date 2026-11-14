import type { MapMode } from '../../state/selection.ts'

const MODES: readonly { value: MapMode; label: string }[] = [
  { value: 'verdict', label: 'Verdict' },
  { value: 'activity', label: 'Activity' },
]

/** Verdict (always harmonized) or Activity (follows the shared Raw / Harmonized control). */
export function MapModeSelector({
  value,
  onChange,
  verdictDisabled = false,
}: {
  value: MapMode
  onChange: (mode: MapMode) => void
  /** True while only raw data exist: there are no verdicts to show yet. */
  verdictDisabled?: boolean
}) {
  return (
    <fieldset className="layer-selector">
      <legend>Map shows</legend>
      {MODES.map((mode) => (
        <label key={mode.value} className={mode.value === 'verdict' && verdictDisabled ? 'is-disabled' : undefined}>
          <input
            type="radio"
            name="map-mode"
            value={mode.value}
            checked={value === mode.value}
            aria-disabled={(mode.value === 'verdict' && verdictDisabled) || undefined}
            onChange={() => {
              if (!(mode.value === 'verdict' && verdictDisabled)) onChange(mode.value)
            }}
          />
          {mode.label}
        </label>
      ))}
    </fieldset>
  )
}
