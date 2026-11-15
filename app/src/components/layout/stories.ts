import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { MONTH_ABBR } from '../../content/calendar.ts'

/** Stories that the app can open: a country, a continent or the world (a fire region has no series here). */
export const selectableStories = (stories: readonly FeaturedStory[] = FEATURED_STORIES) =>
  stories.filter((s) => s.entityType !== 'FIRE_REGION')

export const storyLabel = (s: FeaturedStory) => `${s.entityName}, ${MONTH_ABBR[s.month - 1]} ${s.year}`

/**
 * The story the screen is on: the area AND the month equal the story's. Changing either clears it, so the
 * stored numbers of a story are never shown beside a different area or month (T-072, Lead decision 2).
 */
export function activeStory(
  area: { entity_type: string; entity_id: string },
  month: { year: number; month: number } | null,
  stories: readonly FeaturedStory[] = FEATURED_STORIES,
): FeaturedStory | null {
  if (month === null) return null
  return (
    selectableStories(stories).find(
      (s) =>
        s.entityType === area.entity_type &&
        s.entityId === area.entity_id &&
        s.year === month.year &&
        s.month === month.month,
    ) ?? null
  )
}
