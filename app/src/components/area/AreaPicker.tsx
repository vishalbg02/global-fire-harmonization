import { useId, useState } from 'react'
import type { Bbox, EntityItem } from '../../api/contract.ts'
import { WORLD } from '../../state/selection.ts'
import type { Area } from '../../state/selection.ts'
import { ExportButton } from '../export/ExportButton.tsx'
import { CustomAreaForm } from './CustomAreaForm.tsx'
import type { PolygonControls } from './CustomAreaForm.tsx'
import { filterEntities, matchEntity } from './countryFilter.ts'

interface Props {
  area: Area
  countries: readonly EntityItem[] | undefined
  continents: readonly EntityItem[] | undefined
  /** True if the country or continent list could not be loaded. */
  listsFailed: boolean
  onChooseEntity: (entity: EntityItem) => void
  onChooseWorld: () => void
  onChooseCustom: (bbox: Bbox) => void
  /** The polygon route (T-044): optional, so a picker without it shows the rectangle only. */
  polygon?: PolygonControls
  drawing: boolean
  onToggleDrawing: () => void
  customMessage: string | null
  customLoading: boolean
  /** True while the data are SYNTHETIC (used for the file name only if the server sends none). */
  synthetic: boolean
}

/** Choose the area shown by the calendar and the evidence panel. */
export function AreaPicker({
  area,
  countries,
  continents,
  listsFailed,
  onChooseEntity,
  onChooseWorld,
  onChooseCustom,
  polygon,
  drawing,
  onToggleDrawing,
  customMessage,
  customLoading,
  synthetic,
}: Props) {
  const ids = useId()
  // While the user types, show their text; otherwise show the selected country's name.
  const [typing, setTyping] = useState<string | null>(null)
  const countryName = area.entity_type === 'COUNTRY' ? area.entity_name : ''
  const countryText = typing ?? countryName
  const list = countries ?? []
  const noMatch = typing !== null && typing.trim() !== '' && filterEntities(list, typing).length === 0

  const onCountryChange = (value: string) => {
    const match = matchEntity(list, value)
    if (match !== null) {
      setTyping(null)
      onChooseEntity(match)
    } else {
      setTyping(value)
    }
  }

  return (
    <section className="area-picker" aria-label="Choose an area">
      <h2>Area</h2>
      <p className="legend-note">
        {`Showing: ${area.entity_name}`}
      </p>
      <ExportButton area={area} synthetic={synthetic} />

      <div className="area-row">
        <button type="button" onClick={onChooseWorld} aria-pressed={area.entity_type === 'GLOBAL'}>
          {WORLD.entity_name}
        </button>
      </div>

      <div className="area-row">
        <label htmlFor={`${ids}-country`}>Country</label>
        <input
          id={`${ids}-country`}
          type="search"
          list={`${ids}-countries`}
          value={countryText}
          placeholder="Search for a country"
          autoComplete="off"
          onChange={(e) => onCountryChange(e.target.value)}
          onBlur={() => setTyping(null)}
          aria-describedby={`${ids}-country-help`}
        />
        <datalist id={`${ids}-countries`}>
          {list.map((c) => (
            <option key={c.entity_id} value={c.entity_name} />
          ))}
        </datalist>
        <p id={`${ids}-country-help`} className="legend-note" role="status">
          {noMatch
            ? `No country matches "${typing}".`
            : 'Choose from the countries in the data, or click a country on the map.'}
        </p>
      </div>

      <div className="area-row">
        <label htmlFor={`${ids}-continent`}>Continent</label>
        <select
          id={`${ids}-continent`}
          value={area.entity_type === 'CONTINENT' ? area.entity_id : ''}
          onChange={(e) => {
            const found = (continents ?? []).find((c) => c.entity_id === e.target.value)
            if (found !== undefined) onChooseEntity(found)
          }}
        >
          <option value="">Choose a continent</option>
          {(continents ?? []).map((c) => (
            <option key={c.entity_id} value={c.entity_id}>
              {c.entity_name}
            </option>
          ))}
        </select>
      </div>

      {listsFailed && (
        <p className="form-error" role="alert">
          The country and continent lists could not be loaded. You can still use the world or a custom area.
        </p>
      )}

      <CustomAreaForm
        key={`${area.entity_type === 'CUSTOM' ? area.entity_id : 'none'}-${polygon?.draft?.seq ?? 0}`}
        initial={area.entity_type === 'CUSTOM' && area.polygon === undefined ? area.bbox : null}
        polygon={
          polygon === undefined
            ? undefined
            : {
                ...polygon,
                initial: polygon.draft?.ring ?? (area.entity_type === 'CUSTOM' ? (area.polygon ?? null) : null),
                drawError: polygon.draft?.error ?? null,
                active: area.entity_type === 'CUSTOM' && area.polygon !== undefined,
              }
        }
        onSubmit={onChooseCustom}
        drawing={drawing}
        onToggleDrawing={onToggleDrawing}
        serverMessage={customMessage}
        loading={customLoading}
      />
    </section>
  )
}
