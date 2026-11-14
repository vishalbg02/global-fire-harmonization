import type { MapMode } from '../../state/selection.ts'

const MODES: readonly { value: MapMode; label: string }[] = [
  { value: 'verdict', label: 'Verdict' },
  { value: 'activity', label: 'Activity' },
]

/** Verdict (always harmonized) or Activity (follows the shared Raw / Harmonized control). */
export function MapModeSelector({ value, onChange }: { value: MapMode; onChange: (mode: MapMode) => void }) {
  return (
    <fieldset className="layer-selector">
      <legend>Map shows</legend>
      {MODES.map((mode) => (
        <label key={mode.value}>
          <input
            type="radio"
            name="map-mode"
            value={mode.value}
            checked={value === mode.value}
            onChange={() => onChange(mode.value)}
          />
          {mode.label}
        </label>
      ))}
    </fieldset>
  )
}
