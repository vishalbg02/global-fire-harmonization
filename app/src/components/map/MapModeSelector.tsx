import type { MapMode } from '../../state/selection.ts'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'

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
    <SegmentedControl<MapMode>
      legend="Map shows"
      name="map-mode"
      value={value}
      onChange={onChange}
      options={MODES.map((m) => ({ ...m, disabled: m.value === 'verdict' && verdictDisabled }))}
    />
  )
}
