import { useState } from 'react'
import type { FeaturedStory } from '../../content/featured.ts'
import * as UI from '../../content/ui.ts'
import { Card } from '../ui/Card.tsx'

/**
 * The selected story's headline, caption and facts, all taken from content/featured.ts (never retyped or recomputed).
 * On a phone only the headline shows at first, with a "Read more" toggle, so the verdict stays near the top.
 */
function StoryCaptionBody({ story }: { story: FeaturedStory }) {
  const [expanded, setExpanded] = useState(false)
  const bodyId = 'story-caption-body'
  return (
    <Card className="story-caption" aria-label={UI.STORY_CAPTION_LABEL}>
      <p className="eyebrow">
        {UI.STORY_EYEBROW} <span className="story-label">{story.label}</span>
      </p>
      <h3>{story.headline}</h3>
      <div id={bodyId} className={expanded ? 'story-body' : 'story-body story-body-collapsed'}>
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
      <button type="button" className="story-more" aria-expanded={expanded} aria-controls={bodyId} onClick={() => setExpanded((e) => !e)}>
        {expanded ? UI.STORY_READ_LESS : UI.STORY_READ_MORE}
      </button>
    </Card>
  )
}

export function StoryCaption({ story }: { story: FeaturedStory }) {
  // Keyed by the story, so a new story starts collapsed on a phone.
  return <StoryCaptionBody key={story.label} story={story} />
}
