import type { MeasuredValue, TestStatus, ValidationResults } from '../../api/contract.ts'
import { NOT_MEASURED } from '../../content/testStatus.ts'

export function formatMeasured(value: MeasuredValue): string {
  if (value === null) return NOT_MEASURED
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

export function countStatuses(tests: ValidationResults['tests']): Record<TestStatus, number> {
  const counts: Record<TestStatus, number> = { PASS: 0, FAIL: 0, INCONCLUSIVE: 0, NOT_RUN: 0 }
  for (const t of tests) counts[t.status] += 1
  return counts
}

