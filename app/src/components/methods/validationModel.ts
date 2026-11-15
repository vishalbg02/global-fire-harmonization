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

/**
 * The official entry of a family that has no family-level entry in the results file. Without this table such a family would take the
 * worst status of its entries. Only D1 needs it: the file holds D1-REGIONS (the pooled share over all fire regions), D1-REGIONS-TOTAL,
 * D1-COUNTRIES (supplementary pooled readings), D1-NIGHT and D1-REGIONS-EACH (the night and per-region readings).
 * Source: the Lead's decision on PR #56: the official D1 result is the pooled share; the per-region and night readings are recorded as
 * their own entries, equally visible, with no softer wording (docs/VALIDATION_PLAN.md section 4). Nothing is added to the results file.
 */
export interface OfficialEntry {
  testId: string
  /** The Lead's reading note, in plain words (the wording of docs/VALIDATION_PLAN.md section 4). */
  readingNote: string
  /** What the official entry is, shown beside the family status: "PASS (pooled)". */
  label: string
  /** Measured keys of the official entry shown beside the note, with the stored values. */
  measuredKeys: readonly string[]
  source: string
}

export const OFFICIAL_ENTRY_WITHOUT_FAMILY_ENTRY: Readonly<Record<string, OfficialEntry>> = {
  D1: {
    testId: 'D1-REGIONS',
    label: 'pooled',
    readingNote: 'D1 read as the pooled share as defined; per-region and night shares reported separately (both below 80%).',
    measuredKeys: ['units', 'coverage_90'],
    source: 'Lead decision on PR #56; docs/VALIDATION_PLAN.md section 4',
  },
}

export interface Family {
  key: string
  tests: readonly ValidationTest[]
  /** The family-level entry (test_id equal to the key, or `<key>-FAMILY`), or null when the file has none. */
  headline: ValidationTest | null
  status: TestStatus
  /**
   * 'entry': the status of the family-level entry; 'official': the family has none and the table above names its official entry;
   * 'worst': the family has neither, so it takes the worst status of its entries.
   */
  statusFrom: 'entry' | 'official' | 'worst'
  /** The official entry from the table above, when the family uses it (D1). */
  official: ValidationTest | null
  officialInfo: OfficialEntry | null
  /** For an official entry: the other entries that are not PASS, shown as their own lines under the family (D1: night, per region). */
  separate: readonly ValidationTest[]
  counts: Record<TestStatus, number>
  /** The stored title that says what the family tests (the family-level entry's, else the first entry's). */
  meaning: string
  /** The test_id the overview line links to. */
  anchorTestId: string
}

/** "pooled; 2 sub-readings FAIL" for a family with an official entry: what the status stands for and the other non-PASS readings. */
export function officialSummary(family: Pick<Family, 'officialInfo' | 'separate'>): string | null {
  if (family.officialInfo === null) return null
  const byStatus = new Map<TestStatus, number>()
  for (const s of family.separate) byStatus.set(s.status, (byStatus.get(s.status) ?? 0) + 1)
  const parts = WORST_FIRST.filter((s) => byStatus.has(s)).map((s) => `${byStatus.get(s)} sub-${byStatus.get(s) === 1 ? 'reading' : 'readings'} ${s.replace('_', ' ')}`)
  return `(${family.officialInfo.label})${parts.length > 0 ? `; ${parts.join(', ')}` : ''}`
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
    const info = headline === null ? (OFFICIAL_ENTRY_WITHOUT_FAMILY_ENTRY[key] ?? null) : null
    const official = info === null ? null : (list.find((t) => t.test_id === info.testId) ?? null)
    const first = headline ?? official ?? list[0]!
    const statusFrom = headline !== null ? 'entry' : official !== null ? 'official' : 'worst'
    return {
      key,
      tests: list,
      headline,
      status: headline?.status ?? official?.status ?? worst,
      statusFrom,
      official,
      officialInfo: official === null ? null : info,
      separate: official === null ? [] : list.filter((t) => t !== official && t.status !== 'PASS'),
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
