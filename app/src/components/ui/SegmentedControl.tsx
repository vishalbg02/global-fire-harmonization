import type { ReactNode } from 'react'

export interface SegmentOption<T extends string> {
  value: T
  label: ReactNode
  /** Kept in the tab order (`aria-disabled`); choosing it does nothing here, the caller explains why. */
  disabled?: boolean
  describedBy?: string
}

interface Props<T extends string> {
  legend: string
  name: string
  value: T
  options: readonly SegmentOption<T>[]
  onChange: (value: T) => void
  /** Called when a disabled option is chosen, so the caller can say why. */
  onDisabledChoice?: (value: T) => void
  className?: string
}

/**
 * Radio buttons drawn as segments. They are real radio inputs in a fieldset, so the arrow keys,
 * the group name and the checked state work natively; the visual segment is the label.
 */
export function SegmentedControl<T extends string>({
  legend,
  name,
  value,
  options,
  onChange,
  onDisabledChoice,
  className,
}: Props<T>) {
  return (
    <fieldset className={`layer-selector seg${className === undefined ? '' : ` ${className}`}`}>
      <legend>{legend}</legend>
      <div className="seg-row">
        {options.map((o) => (
          <label key={o.value} className={`seg-option${o.disabled === true ? ' is-disabled' : ''}`}>
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              aria-disabled={o.disabled === true || undefined}
              aria-describedby={o.disabled === true ? o.describedBy : undefined}
              onChange={() => {
                if (o.disabled === true) onDisabledChoice?.(o.value)
                else onChange(o.value)
              }}
            />
            <span>{o.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
