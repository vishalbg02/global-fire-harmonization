import * as UI from '../../content/ui.ts'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'

export type SelectMode = 'country' | 'rectangle' | 'polygon'

/** The mode follows the two drawing flags of the app: none is Country (click to select). */
export function selectMode(drawing: boolean, polygonDrawing: boolean): SelectMode {
  return drawing ? 'rectangle' : polygonDrawing ? 'polygon' : 'country'
}

interface Props {
  mode: SelectMode
  onChange: (mode: SelectMode) => void
  /** The offline copy has the preset views only: drawing is off, Country stays. */
  drawDisabled?: boolean
}

/** Country, Rectangle or Polygon: how a click on the map selects an area. Sits over the map. */
export function MapModeSwitch({ mode, onChange, drawDisabled = false }: Props) {
  return (
    <div className="map-mode">
      <SegmentedControl<SelectMode>
        legend={UI.MAP_MODE_LABEL}
        name="select-mode"
        value={mode}
        onChange={onChange}
        options={[
          { value: 'country', label: UI.MAP_MODES.country },
          { value: 'rectangle', label: UI.MAP_MODES.rectangle, disabled: drawDisabled },
          { value: 'polygon', label: UI.MAP_MODES.polygon, disabled: drawDisabled },
        ]}
      />
      <p className="map-mode-hint" role="status">
        {UI.MAP_MODE_HINT[mode]}
      </p>
    </div>
  )
}
