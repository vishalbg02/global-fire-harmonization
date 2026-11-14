import type { TestStatus } from '../api/contract.ts'

/**
 * How each validation status is shown. Status is always text plus an icon, never colour alone.
 * FAIL and INCONCLUSIVE are drawn at least as strongly as PASS (they are never toned down).
 */
export const TEST_STATUS_PRESENTATION: Record<TestStatus, { label: string; icon: string; meaning: string }> = {
  PASS: { label: 'PASS', icon: '✔', meaning: 'The test ran and met its pass rule.' },
  FAIL: { label: 'FAIL', icon: '✖', meaning: 'The test ran and did not meet its pass rule.' },
  INCONCLUSIVE: { label: 'INCONCLUSIVE', icon: '?', meaning: 'The test ran but could not decide (for example, no mismatch to correct).' },
  NOT_RUN: { label: 'NOT RUN', icon: '–', meaning: 'The test has not been run.' },
}

/** The order the counts are listed in: the failures first, so they are never buried. */
export const STATUS_COUNT_ORDER: readonly TestStatus[] = ['FAIL', 'INCONCLUSIVE', 'PASS', 'NOT_RUN']

export const NOT_MEASURED = 'not measured'

export const NO_TESTS_RUN_MESSAGE =
  'No validation test has been run yet. Results, including failures, will be shown here as they are produced.'
