/**
 * The month control is the timeline scrubber of zone C since T-093 (`components/timeline/Timeline.tsx`): the strip, Play /
 * Pause, previous and next month, and the T-087 picker. This name is kept so the T-043 and T-087 tests (and anything else
 * that imports the month control) keep working with the same props: `months`, `value`, `onChange`.
 */
export { Timeline as MonthSelector } from '../timeline/Timeline.tsx'
export type { TimelineProps as MonthSelectorProps } from '../timeline/Timeline.tsx'
