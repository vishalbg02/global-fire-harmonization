import type { MapLayer } from '../../api/contract.ts'
import { MAP_LAYERS } from '../../api/contract.ts'

const LABELS: Record<MapLayer, string> = {
  verdict: 'Verdict',
  raw: 'Raw',
  harmonized: 'Harmonized',
}

export function LayerSelector({ value, onChange }: { value: MapLayer; onChange: (layer: MapLayer) => void }) {
  return (
    <fieldset className="layer-selector">
      <legend>Map layer</legend>
      {MAP_LAYERS.map((layer) => (
        <label key={layer}>
          <input
            type="radio"
            name="map-layer"
            value={layer}
            checked={value === layer}
            onChange={() => onChange(layer)}
          />
          {LABELS[layer]}
        </label>
      ))}
    </fieldset>
  )
}
