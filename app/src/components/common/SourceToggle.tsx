import { useId } from 'react'
import { HARMONIZED_DESCRIPTION, JUMP_CAPTION, RAW_DESCRIPTION, RAW_UNAVAILABLE, SOURCE_LABELS } from '../../content/source.ts'
import { RAW_ONLY_HARMONIZED_UNAVAILABLE } from '../../content/rawOnly.ts'
import type { Source } from '../../state/selection.ts'

const SOURCES: readonly Source[] = ['raw', 'harmonized']

interface Props {
  value: Source
  onChange: (source: Source) => void
  /** Raw is disabled while the calendar shows % of normal (the contract has no raw baseline). */
  rawDisabled: boolean
  /** True while only raw data exist (T-039): Harmonized is disabled with its reason written out. */
  harmonizedDisabled?: boolean
}

/**
 * The shared Raw / Harmonized control for the map and the calendar. A disabled option stays
 * in the tab order (`aria-disabled`) and its reason is written out, not hidden in a tooltip.
 */
export function SourceToggle({ value, onChange, rawDisabled, harmonizedDisabled = false }: Props) {
  const helpId = useId()
  const describedBy = rawDisabled ? `${helpId}-unavailable` : undefined
  return (
    <fieldset className="layer-selector source-toggle">
      <legend>Data shown</legend>
      {SOURCES.map((source) => {
        const disabled = source === 'raw' ? rawDisabled : harmonizedDisabled
        return (
          <label key={source} className={disabled ? 'is-disabled' : undefined}>
            <input
              type="radio"
              name="data-source"
              value={source}
              checked={value === source}
              aria-disabled={disabled || undefined}
              aria-describedby={disabled ? describedBy : undefined}
              onChange={() => {
                if (!disabled) onChange(source)
              }}
            />
            {SOURCE_LABELS[source]}
          </label>
        )
      })}
      <p className="source-note" id={`${helpId}-description`}>
        {value === 'raw' ? RAW_DESCRIPTION : HARMONIZED_DESCRIPTION}
      </p>
      {harmonizedDisabled && (
        <p className="source-note source-unavailable">{RAW_ONLY_HARMONIZED_UNAVAILABLE}</p>
      )}
      {rawDisabled && (
        <p className="source-note source-unavailable" id={`${helpId}-unavailable`}>
          {RAW_UNAVAILABLE}
        </p>
      )}
      <p className="source-note source-caption">{JUMP_CAPTION}</p>
    </fieldset>
  )
}
