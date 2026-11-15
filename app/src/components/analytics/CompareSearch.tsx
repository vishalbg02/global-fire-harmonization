import type { EntityItem } from '../../api/contract.ts'
import { parseAreaOption, searchAreas } from '../area/areaSearch.ts'
import { Combobox } from '../ui/Combobox.tsx'
import { COMPARE_HELP, COMPARE_LABEL, COMPARE_LISTS_FAILED, COMPARE_NO_MATCH, COMPARE_PLACEHOLDER, COMPARE_RESULTS } from './text.ts'

export interface CompareChoice {
  entityType: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'
  entityId: string
  name: string
}

interface Props {
  countries: readonly EntityItem[] | undefined
  continents: readonly EntityItem[] | undefined
  listsFailed: boolean
  /** The name of the area now compared, shown in the box while the user is not typing. */
  value: string
  onChoose: (choice: CompareChoice) => void
}

/**
 * The "Compare with" search of the Analytics panel (T-090): the same countries, continents and the world as the toolbar's area search,
 * with the same keyboard behaviour (it reuses `Combobox`). The series endpoint serves these three kinds and no other.
 */
export function CompareSearch({ countries, continents, listsFailed, value, onChoose }: Props) {
  return (
    <div className="analytics-compare-search">
      <Combobox
        id="analytics-compare"
        label={COMPARE_LABEL}
        value={value}
        placeholder={COMPARE_PLACEHOLDER}
        help={COMPARE_HELP}
        getOptions={(q) => searchAreas(countries, continents, q)}
        noMatchText={COMPARE_NO_MATCH}
        resultsText={COMPARE_RESULTS}
        onSelect={(option) => {
          const { type, entityId } = parseAreaOption(option.id)
          onChoose({ entityType: type, entityId, name: option.label })
        }}
      />
      {listsFailed && (
        <p className="form-error" role="alert">
          {COMPARE_LISTS_FAILED}
        </p>
      )}
    </div>
  )
}
