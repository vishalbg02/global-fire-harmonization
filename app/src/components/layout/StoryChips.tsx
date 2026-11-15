import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { selectableStories, storyLabel } from './stories.ts'
import * as UI from '../../content/ui.ts'
import { Chip } from '../ui/Chip.tsx'


interface Props {
  stories?: readonly FeaturedStory[]
  areaId: string
  month: { year: number; month: number } | null
  onChoose: (story: FeaturedStory) => void
}

/** The featured stories as chips: one click sets the area and the month. */
export function StoryChips({ stories = FEATURED_STORIES, areaId, month, onChoose }: Props) {
  const list = selectableStories(stories)
  if (list.length === 0) return null
  return (
    <nav className="stories" aria-label={UI.STORIES_NAV}>
      <span className="stories-label">{UI.STORIES_LABEL}</span>
      {list.map((s) => (
        <Chip
          key={s.id}
          selected={month !== null && month.year === s.year && month.month === s.month && areaId === s.entityId}
          onClick={() => onChoose(s)}
          title={s.headline}
        >
          {storyLabel(s)}
        </Chip>
      ))}
    </nav>
  )
}
