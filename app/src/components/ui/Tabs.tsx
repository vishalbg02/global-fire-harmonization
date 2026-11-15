import { useRef } from 'react'
import { nextTabIndex } from './tabKeys.ts'
import type { KeyboardEvent, ReactNode } from 'react'

export interface TabDef<T extends string> {
  id: T
  label: string
  panel: ReactNode
}


interface Props<T extends string> {
  idBase: string
  label: string
  tabs: readonly TabDef<T>[]
  value: T
  onChange: (id: T) => void
}

/** ARIA tabs: one tab stop, arrow keys, Home and End move and select; only the selected panel is rendered. */
export function Tabs<T extends string>({ idBase, label, tabs, value, onChange }: Props<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  const selected = Math.max(0, tabs.findIndex((t) => t.id === value))
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const next = nextTabIndex(selected, tabs.length, e.key)
    if (next === null) return
    e.preventDefault()
    const tab = tabs[next]
    if (tab === undefined) return
    onChange(tab.id)
    refs.current[next]?.focus()
  }
  const active = tabs[selected]
  return (
    <div className="tabs">
      <div role="tablist" aria-label={label} className="tabbar" onKeyDown={onKeyDown}>
        {tabs.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el
            }}
            type="button"
            role="tab"
            id={`${idBase}-tab-${t.id}`}
            aria-selected={i === selected}
            aria-controls={`${idBase}-panel-${t.id}`}
            tabIndex={i === selected ? 0 : -1}
            onClick={() => onChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {active !== undefined && (
        <div
          role="tabpanel"
          id={`${idBase}-panel-${active.id}`}
          aria-labelledby={`${idBase}-tab-${active.id}`}
          tabIndex={0}
          className="tabbody"
        >
          {active.panel}
        </div>
      )}
    </div>
  )
}
