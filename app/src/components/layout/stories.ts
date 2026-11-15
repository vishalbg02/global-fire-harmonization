import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { MONTH_ABBR } from '../../content/calendar.ts'

/** Stories that the app can open: a country, a continent or the world (a fire region has no series here). */
export const selectableStories = (stories: readonly FeaturedStory[] = FEATURED_STORIES) =>
  stories.filter((s) => s.entityType !== 'FIRE_REGION')

export const storyLabel = (s: FeaturedStory) => `${s.entityName}, ${MONTH_ABBR[s.month - 1]} ${s.year}`
