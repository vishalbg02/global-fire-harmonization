import type { Verdict } from '../api/contract.ts'

export interface VerdictPresentation {
  label: string
  /** Icon shown with every verdict so colour is never the only cue. */
  icon: string
  /** Fill colour as RGB. Okabe-Ito derived, colour-blind safe. */
  color: readonly [number, number, number]
  description: string
}

export const VERDICT_PRESENTATION: Record<Verdict, VerdictPresentation> = {
  ABOVE_NORMAL: {
    label: 'Above normal',
    icon: '▲',
    color: [213, 94, 0],
    description: 'Satellite-detected fire activity is likely above the normal range for this month.',
  },
  BELOW_NORMAL: {
    label: 'Below normal',
    icon: '▼',
    color: [0, 114, 178],
    description: 'Satellite-detected fire activity is likely below the normal range for this month.',
  },
  WITHIN_NORMAL: {
    label: 'Within normal',
    icon: '●',
    color: [153, 153, 153],
    description: 'Satellite-detected fire activity is within the normal range for this month.',
  },
  CANNOT_DETERMINE: {
    label: 'Cannot determine',
    icon: '?',
    color: [204, 204, 204],
    description: 'The evidence is too weak for a verdict. This is a result, not an error.',
  },
  NO_DETECTED_ACTIVITY: {
    label: 'No detected activity',
    icon: '○',
    color: [245, 225, 185],
    description: 'No satellite-detected fire activity, and little expected here.',
  },
}
