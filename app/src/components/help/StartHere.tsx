import { useId } from 'react'
import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import {
  START_HERE_EXAMPLES,
  START_HERE_LEDE,
  START_HERE_OWN,
  START_HERE_SEARCH,
  START_HERE_TITLE,
  startHereWorld,
  storyQuestion,
} from '../../content/help.ts'
import { startHereExamples } from './startExamples.ts'
import './help.css'

export interface StartHereProps {
  stories?: readonly FeaturedStory[]
  onChooseStory: (story: FeaturedStory) => void
  onSearch: () => void
  onShowWorld: () => void
  /** The month the world would be shown for, e.g. "October 2026"; null until it is known. */
  worldMonth: string | null
}

/**
 * The answer panel before anything is chosen: what the map answers, three example questions built from the featured
 * stories, and the way to any place or to the whole world.
 */
export function StartHere({ stories = FEATURED_STORIES, onChooseStory, onSearch, onShowWorld, worldMonth }: StartHereProps) {
  const id = useId()
  const examples = startHereExamples(stories)
  return (
    <section className="start-here" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`} className="start-here-title">
        {START_HERE_TITLE}
      </h2>
      <p className="start-here-lede">{START_HERE_LEDE}</p>
      {examples.length > 0 && (
        <>
          <h3 id={`${id}-examples`} className="start-here-label">
            {START_HERE_EXAMPLES}
          </h3>
          <ul className="start-here-list" aria-labelledby={`${id}-examples`}>
            {examples.map((s) => (
              <li key={s.id}>
                <button type="button" className="bare start-here-row" onClick={() => onChooseStory(s)}>
                  <span className="start-here-q">{storyQuestion(s)}</span>
                  <span className="start-here-go" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      <h3 id={`${id}-own`} className="start-here-label">
        {START_HERE_OWN}
      </h3>
      <ul className="start-here-list" aria-labelledby={`${id}-own`}>
        <li>
          <button type="button" className="bare start-here-row" aria-keyshortcuts="/" onClick={onSearch}>
            <span className="start-here-q">{START_HERE_SEARCH}</span>
            <kbd className="start-here-kbd" aria-hidden="true">
              /
            </kbd>
          </button>
        </li>
        <li>
          <button type="button" className="bare start-here-row" onClick={onShowWorld}>
            <span className="start-here-q">{startHereWorld(worldMonth)}</span>
            <span className="start-here-go" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </section>
  )
}
