import type { FeaturedStory } from '../../content/featured.ts'

/** How many example questions "Start here" offers. */
export const START_HERE_COUNT = 3

/** The example questions of "Start here": the first featured stories about a country (the order of featured.ts). */
export function startHereExamples(stories: readonly FeaturedStory[]): FeaturedStory[] {
  return stories.filter((s) => s.entityType === 'COUNTRY').slice(0, START_HERE_COUNT)
}
