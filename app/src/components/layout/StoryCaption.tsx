import { useState } from 'react'
import { STORY_CARD_TITLE } from '../../content/answer.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import * as UI from '../../content/ui.ts'
import { rememberStoryOpen, storyOpenAtStart } from './storyCard.ts'

/**
 * The featured story on screen, as a quiet "Story" card: its label ([VERIFIED]) and headline in the header, which opens
 * and closes the caption, notes, context, source line, query and report link, all taken from content/featured.ts
 * (never retyped or recomputed). Open by default; closed, it stays closed for the rest of the session.
 */
export function StoryCaption({ story }: { story: FeaturedStory }) {
  const [open, setOpen] = useState(() => storyOpenAtStart())
  const bodyId = 'story-caption-body'
  const toggle = () => {
    const next = !open
    setOpen(next)
    rememberStoryOpen(next)
  }
  return (
    <section className="story-card" aria-label={UI.STORY_CAPTION_LABEL} data-open={open}>
      <h3 className="story-card-head">
        <button type="button" className="bare story-toggle" aria-expanded={open} aria-controls={bodyId} onClick={toggle}>
          <span className="story-kicker">
            {STORY_CARD_TITLE} <span className="story-label">{story.label}</span>
          </span>
          <span className="story-headline">{story.headline}</span>
          <span className="story-chevron" aria-hidden="true" />
        </button>
      </h3>
      <div id={bodyId} className="story-body" hidden={!open}>
        <p>{story.caption}</p>
        {story.notes.map((n) => (
          <p key={n} className="story-note">
            {n}
          </p>
        ))}
        <p className="story-note">{`${UI.STORY_CONTEXT_PREFIX} ${story.context}.`}</p>
        <p className="source-line">{story.sourceLine}</p>
        <p className="source-line">
          {`${UI.STORY_QUERY_PREFIX} ${story.query}. `}
          <a href={story.reportHref} target="_blank" rel="noreferrer">
            {UI.STORY_REPORT_LINK}
          </a>
        </p>
      </div>
    </section>
  )
}
