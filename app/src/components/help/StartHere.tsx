import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'

export interface StartHereProps {
  stories?: readonly FeaturedStory[]
  onChooseStory: (story: FeaturedStory) => void
  onSearch: () => void
  onShowWorld: () => void
  /** The month the world would be shown for, e.g. "October 2026"; null until it is known. */
  worldMonth: string | null
}

/** The answer panel before anything is chosen: example questions from the featured stories, and the way to any place. */
export function StartHere({ stories = FEATURED_STORIES, onChooseStory, onSearch, onShowWorld, worldMonth }: StartHereProps) {
  const examples = stories.filter((s) => s.entityType === 'COUNTRY').slice(0, 3)
  return (
    <section className="start-here" aria-label="Start here">
      <h2>Start here</h2>
      <ul>
        {examples.map((s) => (
          <li key={s.id}>
            <button type="button" onClick={() => onChooseStory(s)}>
              {s.headline}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" onClick={onSearch}>
        Search any country
      </button>
      <button type="button" onClick={onShowWorld}>
        {worldMonth === null ? 'Show the whole world' : `Show the whole world for ${worldMonth}`}
      </button>
    </section>
  )
}
