import type { FeaturedStory } from '../../content/featured.ts'
import * as UI from '../../content/ui.ts'
import { Card } from '../ui/Card.tsx'

/** The selected story's headline, caption and facts, all taken from content/featured.ts (never retyped or recomputed). */
export function StoryCaption({ story }: { story: FeaturedStory }) {
  return (
    <Card className="story-caption" aria-label={UI.STORY_CAPTION_LABEL}>
      <p className="eyebrow">
        {UI.STORY_EYEBROW} <span className="story-label">{story.label}</span>
      </p>
      <h3>{story.headline}</h3>
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
    </Card>
  )
}
