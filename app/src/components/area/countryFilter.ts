import type { EntityItem } from '../../api/contract.ts'

/** The entity whose name equals `text`, ignoring case and surrounding spaces; null if none. */
export function matchEntity(entities: readonly EntityItem[], text: string): EntityItem | null {
  const wanted = text.trim().toLowerCase()
  if (wanted === '') return null
  return entities.find((e) => e.entity_name.toLowerCase() === wanted) ?? null
}

/** The entities whose name contains `text` (case-insensitive); all of them for empty text. */
export function filterEntities(entities: readonly EntityItem[], text: string): EntityItem[] {
  const wanted = text.trim().toLowerCase()
  if (wanted === '') return [...entities]
  return entities.filter((e) => e.entity_name.toLowerCase().includes(wanted))
}
