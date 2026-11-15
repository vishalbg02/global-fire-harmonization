import type { EntityItem } from '../../api/contract.ts'
import * as UI from '../../content/ui.ts'
import type { Area } from '../../state/selection.ts'
import { Combobox } from '../ui/Combobox.tsx'
import { parseAreaOption, searchAreas } from './areaSearch.ts'

interface Props {
  area: Area
  countries: readonly EntityItem[] | undefined
  continents: readonly EntityItem[] | undefined
  listsFailed: boolean
  onChooseEntity: (entity: EntityItem) => void
  onChooseWorld: () => void
}

/** The area search of the toolbar: countries and continents (and the world), by keyboard or pointer. */
export function AreaSearch({ area, countries, continents, listsFailed, onChooseEntity, onChooseWorld }: Props) {
  return (
    <div className="area-search">
      <Combobox
        id="area-search"
        label={UI.SEARCH_LABEL}
        value={area.entity_type === 'CUSTOM' ? '' : area.entity_name}
        placeholder={area.entity_type === 'CUSTOM' ? area.entity_name : UI.SEARCH_PLACEHOLDER}
        help={UI.SEARCH_HELP}
        getOptions={(q) => searchAreas(countries, continents, q)}
        noMatchText={UI.SEARCH_NO_MATCH}
        resultsText={UI.SEARCH_RESULTS}
        onSelect={(o) => {
          const { type, entityId } = parseAreaOption(o.id)
          if (type === 'GLOBAL') return onChooseWorld()
          const found = (type === 'COUNTRY' ? countries : continents)?.find((e) => e.entity_id === entityId)
          if (found !== undefined) onChooseEntity(found)
        }}
      />
      {listsFailed && (
        <p className="form-error" role="alert">
          {UI.SEARCH_LISTS_FAILED}
        </p>
      )}
    </div>
  )
}
