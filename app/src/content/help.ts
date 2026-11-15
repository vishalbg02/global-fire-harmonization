// Help texts of the app (T-093): the "?" explainers, the guided tour, the Help sheet, the Start-here state, the keyboard
// shortcuts and the one-line hints. The explainers reuse the approved glossary of plainLanguage.ts word for word wherever
// it has the term; the new sentences are in the same voice and are checked by help.test.ts (no cause, forecast, fire
// count, burned area or accuracy claim). The Lead reviews the wording.
import type { FeaturedStory } from './featured.ts'
import { GLOSSARY } from './plainLanguage.ts'
import { monthLabel } from '../state/months.ts'

// ---- "?" explainers ----

export type ExplainerId =
  | 'pct-of-normal'
  | 'interval-90'
  | 'probability'
  | 'cell-days'
  | 'cannot-determine'
  | 'no-detected-activity'
  | 'provisional'
  | 'raw-vs-harmonized'
  | 'satellite-view'
  | 'normal-range'

export interface Explainer {
  readonly term: string
  readonly text: string
  /** The anchor on the methods page that "Learn more" opens. */
  readonly anchor: string
}

const glossary = (id: string): string => {
  const entry = GLOSSARY.find((g) => g.id === id)
  if (entry === undefined) throw new Error(`No glossary entry "${id}"`)
  return entry.hint
}

export const EXPLAINERS: Record<ExplainerId, Explainer> = {
  'pct-of-normal': { term: '% of normal', text: glossary('pct-of-normal'), anchor: 'baseline-verdicts' },
  'interval-90': { term: '90% interval', text: glossary('interval-90'), anchor: 'combining' },
  probability: {
    term: 'probability',
    text: 'The chance, given the 90% interval, that the month lies above, within or below the normal range. A verdict is given only from 80%.',
    anchor: 'baseline-verdicts',
  },
  'cell-days': {
    term: 'Aqua-equivalent cell-days',
    text: `${glossary('cell-day')} ${glossary('aqua-equivalent')}`,
    anchor: 'calibration',
  },
  'cannot-determine': { term: 'cannot determine', text: glossary('cannot-determine'), anchor: 'baseline-verdicts' },
  'no-detected-activity': {
    term: 'no detected activity',
    text: 'No satellite detected a hotspot here this month, and little is expected in a normal year. It is a result of its own, not a missing value.',
    anchor: 'baseline-verdicts',
  },
  provisional: { term: 'provisional', text: glossary('provisional'), anchor: 'sources' },
  'raw-vs-harmonized': {
    term: 'Raw and Harmonized',
    text: `${glossary('raw')} ${glossary('harmonized')}`,
    anchor: 'why-not-add',
  },
  'satellite-view': {
    term: 'Satellite view',
    text: 'A true-colour picture from the Aqua satellite for one day of the selected month. It is context, not data: it has clouds and gaps, and it does not change a verdict.',
    anchor: 'sources',
  },
  'normal-range': { term: 'normal range', text: glossary('normal-range'), anchor: 'baseline-verdicts' },
}

export const EXPLAINER_LEARN_MORE = 'Learn more'
/** The accessible name of a "?" button. */
export const explainerLabel = (term: string) => `What is ${term}?`

// ---- The guided tour ----

/** The element a tour step points at: `data-tour` on the real UI. */
export type TourAnchor = 'place' | 'month' | 'verdict' | 'why' | 'raw'

export interface TourStep {
  readonly id: TourAnchor
  readonly title: string
  readonly text: string
  /** Where the step points when its own anchor is not on screen (the reasons appear only with an answer). */
  readonly fallback?: TourAnchor
}

export const TOUR_LABEL = 'Guided tour'

export const TOUR_STEPS: readonly TourStep[] = [
  {
    id: 'place',
    title: 'Pick a place',
    text: 'Search for a country or continent here, or click a country on the map; you can also draw your own area.',
  },
  {
    id: 'month',
    title: 'Pick a month',
    text: 'Choose any month from 2002 to the latest data on this timeline, or play the months in order.',
  },
  {
    id: 'verdict',
    title: 'Read the verdict',
    text: 'The answer for your place and month appears here: above, within or below the normal range, or "cannot determine". Until you choose, it offers three example questions.',
  },
  {
    id: 'why',
    title: 'Why this verdict',
    text: 'With every answer, "Why" lists the reasons for the verdict, and Details below the map hold the evidence from each satellite.',
    fallback: 'verdict',
  },
  {
    id: 'raw',
    title: 'Raw vs harmonized',
    text: 'Layers switches the map between the raw detections of each satellite and the harmonized estimate, which puts them on one scale so that months from different satellites can be compared.',
  },
]

export const TOUR_NEXT = 'Next'
export const TOUR_BACK = 'Back'
export const TOUR_SKIP = 'Skip tour'
export const TOUR_DONE = 'Done'
export const TOUR_MORE_HELP = 'More help'
/** "1 of 5". */
export const tourCount = (index: number, total: number) => `${index + 1} of ${total}`

// ---- The Help sheet ----

export const HELP_SHEET_TITLE = 'Help'
export const HELP_CLOSE = 'Close'
export const HELP_TAKE_TOUR = 'Take the tour'
export const HELP_TAKE_TOUR_NOTE = 'Five short steps on the map itself.'
export const HELP_SHORTCUTS_LINK = 'Keyboard shortcuts'
export const HELP_METHODS_LINK = 'Methods and validation'

// ---- Keyboard shortcuts ----

export const SHORTCUTS_TITLE = 'Keyboard shortcuts'
export const SHORTCUTS_NOTE = 'Shortcuts do nothing while you type in a field or while a dialog is open; Esc always closes.'

export type ShortcutId =
  | 'month-prev'
  | 'month-next'
  | 'year-prev'
  | 'year-next'
  | 'play'
  | 'globe'
  | 'satellite'
  | 'search'
  | 'shortcuts'
  | 'close'

export interface ShortcutRow {
  /** The keys as printed, each in its own <kbd>. */
  readonly keys: readonly string[]
  readonly label: string
  readonly ids: readonly ShortcutId[]
}

export const SHORTCUT_ROWS: readonly ShortcutRow[] = [
  { keys: ['←', '→'], label: 'Previous or next month', ids: ['month-prev', 'month-next'] },
  { keys: ['Page Down', 'Page Up'], label: 'Previous or next year', ids: ['year-prev', 'year-next'] },
  { keys: ['Space'], label: 'Play or pause the months', ids: ['play'] },
  { keys: ['G'], label: 'Switch between the flat map and the globe', ids: ['globe'] },
  { keys: ['S'], label: 'Satellite view on or off', ids: ['satellite'] },
  { keys: ['/'], label: 'Search for a place', ids: ['search'] },
  { keys: ['?'], label: 'Show these shortcuts', ids: ['shortcuts'] },
  { keys: ['Esc'], label: 'Close the help, a dialog or a popup', ids: ['close'] },
]

// ---- Start here ----

export const START_HERE_TITLE = 'Start here'
export const START_HERE_LEDE =
  'This map answers one question: was satellite-detected fire activity in a place and month above, within or below its normal range?'
export const START_HERE_EXAMPLES = 'Example questions'
export const START_HERE_OWN = 'Or choose your own'
export const START_HERE_SEARCH = 'Search any country'
export const START_HERE_WORLD = 'Show the whole world'
export const startHereWorld = (month: string | null) => (month === null ? START_HERE_WORLD : `${START_HERE_WORLD} for ${month}`)

/** The possessive of a place name: "Indonesia's", "the Philippines'". */
export const possessive = (name: string) => (name.endsWith('s') ? `${name}'` : `${name}'s`)

/** An example question built from a featured story's own fields, e.g. "Was Indonesia's fire activity in September 2015 unusual?". */
export const storyQuestion = (story: Pick<FeaturedStory, 'entityName' | 'year' | 'month'>) =>
  `Was ${possessive(story.entityName)} fire activity in ${monthLabel(story)} unusual?`

// ---- One-line hints ----

/** Shown once, the first time the user turns the map into a globe. */
export const globeHint = (mac: boolean) => `Drag to turn the Earth; ${mac ? '⌘' : 'Ctrl'} + scroll to zoom`
