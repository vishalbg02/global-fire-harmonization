// Help texts of the app (T-093): the "?" explainers, the guided tour, the Start-here state, the shortcuts and the hints.
// The explainers reuse the approved glossary of plainLanguage.ts word for word wherever it has the term; the few new
// sentences are in the same voice and are checked by help.test.ts (no cause, forecast, fire count or burned area).
import { GLOSSARY } from './plainLanguage.ts'

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
  'interval-90': { term: '90% interval', text: glossary('interval-90'), anchor: 'baseline-verdicts' },
  probability: {
    term: 'probability',
    text: 'The chance, given the 90% interval, that the month lies above, within or below the normal range. A verdict is given only from 80%.',
    anchor: 'baseline-verdicts',
  },
  'cell-days': {
    term: 'Aqua-equivalent cell-days',
    text: `${glossary('cell-day')} ${glossary('aqua-equivalent')}`,
    anchor: 'baseline-verdicts',
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
    anchor: 'baseline-verdicts',
  },
  'satellite-view': {
    term: 'Satellite view',
    text: 'A true-colour picture from the Aqua satellite for one day of the selected month. It is context, not data: it has clouds and gaps, and it does not change a verdict.',
    anchor: 'sources',
  },
  'normal-range': { term: 'normal range', text: glossary('normal-range'), anchor: 'baseline-verdicts' },
}
