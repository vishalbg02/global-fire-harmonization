/**
 * Plain-language texts (T-076): "How to read this", glossary hints and the method in plain words.
 *
 * Every statement restates the approved method (D-028 baseline and verdicts, D-031, docs/NUMBER_INVENTORY.md) or what the products
 * store. Nothing here gives a cause, a forecast, a fire count or a burned area: a hotspot is a satellite detection, not a fire.
 * The Lead reviews the wording; the UI that shows these texts is T-070 to T-072 (Member 3).
 */

export interface HowToReadStep {
  readonly id: string
  readonly title: string
  readonly text: string
}

export const HOW_TO_READ_TITLE = 'How to read this'

export const HOW_TO_READ: readonly HowToReadStep[] = [
  {
    id: 'pick',
    title: 'Pick a place and a month',
    text: 'Choose a country, a continent or a world region, and a month from 2002 to the latest data, on the map or in the calendar.',
  },
  {
    id: 'verdict',
    title: 'Read the verdict',
    text: 'The verdict says whether satellite-detected fire activity in that month was above, within or below the normal range for the same calendar month in 2003 to 2022. It does not say that something unusual happened.',
  },
  {
    id: 'percent',
    title: 'Read "% of normal"',
    text: '100% is a typical month, the middle of those 20 years. 265% is about two and a half times as much detected activity as a typical month; 50% is half as much.',
  },
  {
    id: 'interval',
    title: 'Read the uncertainty',
    text: 'The estimate comes with a 90% range, the interval in which the true value most likely lies. "More than 99% likely above normal" is the chance, given that range, that the month lies above the normal range.',
  },
  {
    id: 'cannot',
    title: '"Cannot determine" is a result',
    text: 'It means the evidence is too weak or too uncertain for a verdict, for example when satellite data are missing or the normal range is too small to judge. It does not mean the month was normal.',
  },
  {
    id: 'unit',
    title: 'What is being counted',
    text: 'Fire-active cell-days: a small map cell counts once for each day a satellite detected a hotspot in it. This is not the number of fires and not the area burned.',
  },
]

export interface GlossaryEntry {
  readonly id: string
  readonly term: string
  readonly hint: string
}

export const GLOSSARY: readonly GlossaryEntry[] = [
  {
    id: 'cell-day',
    term: 'Fire-active cell-day',
    hint: 'One small map cell with at least one satellite hotspot on one day. It measures how widely and how long fire was detected, not how many fires there were or how much burned.',
  },
  {
    id: 'aqua-equivalent',
    term: 'Aqua-equivalent',
    hint: 'Counts from the other satellites are converted to the scale of the Aqua satellite, which has the longest record, so that months from different satellites can be compared.',
  },
  {
    id: 'harmonized',
    term: 'Harmonized estimate',
    hint: 'One estimate per area and month made by converting each satellite to the same scale and combining them, with an uncertainty range.',
  },
  {
    id: 'normal-range',
    term: 'Normal range',
    hint: 'The middle half of the same calendar month in 2003 to 2022 (from the 25th to the 75th percentile of the years with an estimate).',
  },
  {
    id: 'pct-of-normal',
    term: '% of normal',
    hint: 'The estimate divided by the typical (median) value of that calendar month in 2003 to 2022. 100% is typical.',
  },
  {
    id: 'interval-90',
    term: '90% interval',
    hint: 'The range in which the estimate most likely lies, given the uncertainty of the satellites and of the conversion. A wide range means a less certain month.',
  },
  {
    id: 'verdict',
    term: 'Verdict',
    hint: 'Above normal, within normal or below normal, given only when the data support it with at least 80% probability. Otherwise "cannot determine" or "no detected activity".',
  },
  {
    id: 'cannot-determine',
    term: 'Cannot determine',
    hint: 'A result, not an error: the data cannot support a verdict. The reason is listed under "Why".',
  },
  {
    id: 'provisional',
    term: 'Provisional',
    hint: 'Recent months use near-real-time data, which may change when science-quality data arrive.',
  },
  {
    id: 'raw',
    term: 'Raw view',
    hint: 'The detections as the satellites reported them, not converted and not combined. The satellites are not comparable in this view.',
  },
]

export const IN_PLAIN_WORDS_TITLE = 'In plain words'

/** A short summary for the top of the methods page. The sections below it keep the approved technical wording. */
export const IN_PLAIN_WORDS: readonly string[] = [
  'Several satellites detect hotspots from space. They differ in sensitivity and in the times of day they pass over, so their raw counts cannot simply be added up or compared across the years.',
  'This tool converts each satellite to one common scale, combines them for every area and month, and gives an uncertainty range with each estimate.',
  'It then compares each month with the same calendar month in 2003 to 2022. The verdict is "above", "within" or "below" the normal range only when the data support it with at least 80% probability; otherwise it says "cannot determine".',
  'What it measures is satellite-detected fire activity, counted as fire-active cell-days. It does not count fires, measure burned area or say why activity was high or low.',
  'Where the evidence is weak, the tool says so, and the methods page lists the tests that were run, including the ones that failed.',
]
