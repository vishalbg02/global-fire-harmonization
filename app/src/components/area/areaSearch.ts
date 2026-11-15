import type { EntityItem } from '../../api/contract.ts'
import type { ComboOption } from '../ui/Combobox.tsx'
import { SEARCH_KIND, WORLD_BUTTON } from '../../content/ui.ts'

export const MAX_SEARCH_RESULTS = 10

/**
 * The options of the area search: countries and continents whose name (or code) matches the
 * text. Names that start with the text come first, then names that contain it; each group keeps
 * its order. Empty text lists the continents first (a short list), then countries.
 */
export function searchAreas(
  countries: readonly EntityItem[] | undefined,
  continents: readonly EntityItem[] | undefined,
  text: string,
  limit: number = MAX_SEARCH_RESULTS,
): ComboOption[] {
  const wanted = text.trim().toLowerCase()
  const all: ComboOption[] = [
    { id: 'GLOBAL:GLOBAL', label: WORLD_BUTTON, hint: SEARCH_KIND.GLOBAL },
    ...(continents ?? []).map((c) => ({ id: `CONTINENT:${c.entity_id}`, label: c.entity_name, hint: SEARCH_KIND.CONTINENT })),
    ...(countries ?? []).map((c) => ({ id: `COUNTRY:${c.entity_id}`, label: c.entity_name, hint: SEARCH_KIND.COUNTRY })),
  ]
  if (wanted === '') return all.slice(0, limit)
  const code = (o: ComboOption) => o.id.slice(o.id.indexOf(':') + 1).toLowerCase()
  const starts = all.filter((o) => o.label.toLowerCase().startsWith(wanted) || code(o) === wanted)
  const contains = all.filter((o) => !starts.includes(o) && o.label.toLowerCase().includes(wanted))
  return [...starts, ...contains].slice(0, limit)
}

/** Splits an option id back into its type and entity id. */
export function parseAreaOption(id: string): { type: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'; entityId: string } {
  const i = id.indexOf(':')
  return { type: id.slice(0, i) as 'COUNTRY' | 'CONTINENT' | 'GLOBAL', entityId: id.slice(i + 1) }
}
