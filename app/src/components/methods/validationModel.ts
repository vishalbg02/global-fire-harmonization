import type { MeasuredValue, TestStatus, ValidationTest } from '../../api/contract.ts'

/**
 * Pure helpers of the validation overview (T-089). Nothing here changes a stored value: a status is only ever one the file holds,
 * a measured value is shown exactly as stored, and a family without its own entry takes the worst status of its entries.
 */

export type StatusFilter = 'ALL' | TestStatus

/** Worst first: a family without a family-level entry takes the first status of this list that one of its entries has. */
export const WORST_FIRST: readonly TestStatus[] = ['FAIL', 'INCONCLUSIVE', 'NOT_RUN', 'PASS']

/** The family of an entry: the part of its test_id before the first hyphen (A1-C3 and A1-FAMILY belong to A1). */
export const familyKey = (testId: string): string => testId.split('-')[0] ?? testId

export interface Family {
  key: string
  tests: readonly ValidationTest[]
  /** The family-level entry (test_id equal to the key, or `<key>-FAMILY`), or null when the file has none. */
  headline: ValidationTest | null
  status: TestStatus
  /** 'entry': the status of the family-level entry; 'worst': the worst status of the entries (the file has no family-level entry). */
  statusFrom: 'entry' | 'worst'
  counts: Record<TestStatus, number>
  /** The stored title that says what the family tests (the family-level entry's, else the first entry's). */
  meaning: string
  /** The test_id the overview line links to. */
  anchorTestId: string
}

export const emptyCounts = (): Record<TestStatus, number> => ({ PASS: 0, FAIL: 0, INCONCLUSIVE: 0, NOT_RUN: 0 })

export function countByStatus(tests: readonly Pick<ValidationTest, 'status'>[]): Record<TestStatus, number> {
  const counts = emptyCounts()
  for (const t of tests) counts[t.status] += 1
  return counts
}

/** "Real anomaly preserved: family result" reads "Real anomaly preserved"; every other title is unchanged. */
export const meaningOf = (title: string): string => title.replace(/:\s*family result\s*$/i, '')

/** The families of the file in the order of their first entry. */
export function groupFamilies(tests: readonly ValidationTest[]): Family[] {
  const byKey = new Map<string, ValidationTest[]>()
  for (const t of tests) {
    const key = familyKey(t.test_id)
    const list = byKey.get(key)
    if (list === undefined) byKey.set(key, [t])
    else list.push(t)
  }
  return [...byKey.entries()].map(([key, list]) => {
    const headline = list.find((t) => t.test_id === key || t.test_id === `${key}-FAMILY`) ?? null
    const counts = countByStatus(list)
    const worst = WORST_FIRST.find((s) => counts[s] > 0) ?? 'NOT_RUN'
    const first = headline ?? list[0]!
    return {
      key,
      tests: list,
      headline,
      status: headline?.status ?? worst,
      statusFrom: headline === null ? 'worst' : 'entry',
      counts,
      meaning: meaningOf(first.title),
      anchorTestId: first.test_id,
    }
  })
}

export function filterTests(tests: readonly ValidationTest[], filter: StatusFilter): ValidationTest[] {
  return filter === 'ALL' ? [...tests] : tests.filter((t) => t.status === filter)
}

/** The element id of one entry's detail (test ids are letters, digits and hyphens). */
export const testAnchor = (testId: string): string => `test-${testId}`

/** A readable label from a stored measured key: underscores become spaces, a dot becomes " › ", the first letter is capital. */
export function measuredLabel(key: string): string {
  const text = key.replaceAll('.', ' › ').replaceAll('_', ' ').replace(/\s+/g, ' ').trim()
  return text === '' ? key : text.charAt(0).toUpperCase() + text.slice(1)
}

/** A measured value exactly as stored: a number or text as it is, true/false, and null as "not measured". */
export function measuredText(value: MeasuredValue, notMeasured: string): string {
  if (value === null) return notMeasured
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

/** Failing and inconclusive entries start open so that every failure and its notes are visible without a click. */
export const startsOpen = (status: TestStatus): boolean => status === 'FAIL' || status === 'INCONCLUSIVE'
