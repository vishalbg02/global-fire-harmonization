import { moveActive } from './comboKeys.ts'
import { useState } from 'react'
import type { KeyboardEvent } from 'react'

export interface ComboOption {
  id: string
  label: string
  hint?: string
}


interface Props {
  id: string
  label: string
  /** The options for the text typed so far (the caller filters). */
  getOptions: (query: string) => readonly ComboOption[]
  onSelect: (option: ComboOption) => void
  /** Shown while the user is not typing (the selected area). */
  value: string
  placeholder?: string
  help?: string
  noMatchText: (query: string) => string
  resultsText: (count: number) => string
  /** For tests: render open with this text typed. */
  initialQuery?: string
  initialOpen?: boolean
}

/** A combobox with a list box (ARIA 1.2 pattern): arrows move, Enter chooses, Escape closes, focus stays in the input. */
export function Combobox({
  id,
  label,
  getOptions,
  onSelect,
  value,
  placeholder,
  help,
  noMatchText,
  resultsText,
  initialQuery,
  initialOpen = false,
}: Props) {
  const [query, setQuery] = useState<string | null>(initialQuery ?? null)
  const [open, setOpen] = useState(initialOpen)
  const [active, setActive] = useState(initialOpen ? 0 : -1)
  const text = query ?? value
  const options = open ? getOptions(query ?? '') : []
  const listId = `${id}-list`
  const optionId = (i: number) => `${id}-opt-${i}`
  const typed = (query ?? '').trim()

  const choose = (o: ComboOption) => {
    setOpen(false)
    setQuery(null)
    setActive(-1)
    onSelect(o)
  }
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (!open) {
        setOpen(true)
        setActive(e.key === 'ArrowDown' ? 0 : Math.max(0, getOptions(query ?? '').length - 1))
      } else setActive(moveActive(active, options.length, e.key))
    } else if (e.key === 'Enter') {
      const o = options[active]
      if (open && o !== undefined) {
        e.preventDefault()
        choose(o)
      }
    } else if (e.key === 'Escape') {
      if (open || query !== null) {
        e.preventDefault()
        setOpen(false)
        setQuery(null)
        setActive(-1)
      }
    } else if (e.key === 'Tab') setOpen(false)
  }
  const status = !open ? '' : options.length === 0 ? noMatchText(typed) : resultsText(options.length)

  return (
    <div className="combo">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && active >= 0 && options[active] !== undefined ? optionId(active) : undefined}
        aria-describedby={help === undefined ? undefined : `${id}-help`}
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActive(0)
        }}
        onFocus={(e) => e.target.select()}
        onBlur={() => {
          setOpen(false)
          setQuery(null)
          setActive(-1)
        }}
        onKeyDown={onKeyDown}
      />
      {help !== undefined && (
        <span id={`${id}-help`} className="visually-hidden">
          {help}
        </span>
      )}
      <ul id={listId} role="listbox" aria-label={label} className="combo-list" hidden={!open || options.length === 0}>
        {options.map((o, i) => (
          <li
            key={o.id}
            id={optionId(i)}
            role="option"
            aria-selected={i === active}
            className={i === active ? 'combo-option combo-active' : 'combo-option'}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => choose(o)}
            onMouseEnter={() => setActive(i)}
          >
            <span>{o.label}</span>
            {o.hint !== undefined && <span className="combo-hint">{o.hint}</span>}
          </li>
        ))}
      </ul>
      {open && options.length === 0 && <p className="combo-empty">{noMatchText(typed)}</p>}
      <p role="status" className="visually-hidden">
        {status}
      </p>
    </div>
  )
}
