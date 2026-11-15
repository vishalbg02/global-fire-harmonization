import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { parseValidationResults } from '../../api/contract.ts'
import type { ValidationTest } from '../../api/contract.ts'
import { countByStatus, familyKey, filterTests, groupFamilies, measuredLabel, measuredText, meaningOf, startsOpen, testAnchor } from './validationModel.ts'

// SYNTHETIC entries (labelled): the rules of the model on small known cases.
const entry = (test_id: string, status: ValidationTest['status'], title = `Title ${test_id}`): ValidationTest => ({
  test_id, family: test_id.charAt(0), title, case: 'c', criterion: 'r', threshold: 't', measured: {}, status, notes: '',
})

describe('family key and status rule', () => {
  it('takes the part of the id before the first hyphen', () => {
    expect(familyKey('A1-C3')).toBe('A1')
    expect(familyKey('A1-FAMILY')).toBe('A1')
    expect(familyKey('B1-2012-01')).toBe('B1')
    expect(familyKey('CTRL-SHARED-BASELINE')).toBe('CTRL')
    expect(familyKey('E1')).toBe('E1')
  })

  it('uses the family-level entry when the file has one, even if other entries differ', () => {
    const [a1, d] = groupFamilies([entry('A1-C1', 'PASS'), entry('A1-C2', 'FAIL'), entry('A1-FAMILY', 'PASS', 'Real anomaly: family result'), entry('B1', 'FAIL'), entry('B1-X', 'PASS')])
    expect(a1).toMatchObject({ key: 'A1', status: 'PASS', statusFrom: 'entry', meaning: 'Real anomaly', counts: { PASS: 2, FAIL: 1, INCONCLUSIVE: 0, NOT_RUN: 0 } })
    expect(d).toMatchObject({ key: 'B1', status: 'FAIL', statusFrom: 'entry' })
  })

  it('takes the worst status of the entries when there is no family-level entry', () => {
    const [f] = groupFamilies([entry('D1-REGIONS', 'PASS', 'Pooled coverage'), entry('D1-NIGHT', 'FAIL'), entry('D1-COUNTRIES', 'PASS')])
    expect(f).toMatchObject({ key: 'D1', status: 'FAIL', statusFrom: 'worst', headline: null, meaning: 'Pooled coverage', anchorTestId: 'D1-REGIONS' })
    expect(groupFamilies([entry('X-1', 'PASS'), entry('X-2', 'INCONCLUSIVE')])[0]?.status).toBe('INCONCLUSIVE')
    expect(groupFamilies([entry('X-1', 'PASS'), entry('X-2', 'NOT_RUN')])[0]?.status).toBe('NOT_RUN')
    expect(groupFamilies([entry('X-1', 'PASS'), entry('X-2', 'PASS')])[0]?.status).toBe('PASS')
  })

  it('keeps the families in the order of their first entry', () => {
    expect(groupFamilies([entry('B1', 'PASS'), entry('A1-C1', 'PASS'), entry('B1-2', 'PASS')]).map((f) => f.key)).toEqual(['B1', 'A1'])
  })

  it('removes only a trailing ": family result" from a title', () => {
    expect(meaningOf('Same fire, two eras: family result')).toBe('Same fire, two eras')
    expect(meaningOf('Family result of the control')).toBe('Family result of the control')
  })
})

describe('filter, counts, labels, values', () => {
  const tests = [entry('T1', 'FAIL'), entry('T2', 'PASS'), entry('T3', 'FAIL'), entry('T4', 'INCONCLUSIVE')]
  it('filters by status and keeps the file order; ALL shows every entry', () => {
    expect(filterTests(tests, 'FAIL').map((t) => t.test_id)).toEqual(['T1', 'T3'])
    expect(filterTests(tests, 'PASS')).toHaveLength(1)
    expect(filterTests(tests, 'NOT_RUN')).toHaveLength(0)
    expect(filterTests(tests, 'ALL')).toHaveLength(4)
    expect(countByStatus(tests)).toEqual({ PASS: 1, FAIL: 2, INCONCLUSIVE: 1, NOT_RUN: 0 })
  })

  it('makes a readable label from the stored key', () => {
    expect(measuredLabel('coverage_90')).toBe('Coverage 90')
    expect(measuredLabel('widening_factor_reported_not_applied.c_for_90')).toBe('Widening factor reported not applied › c for 90')
    expect(measuredLabel('units')).toBe('Units')
    expect(measuredLabel('')).toBe('')
  })

  it('shows values exactly as stored', () => {
    expect(measuredText(0.8178717598908595, 'not measured')).toBe('0.8178717598908595')
    expect(measuredText(1466, 'not measured')).toBe('1466')
    expect(measuredText('2017-2018 only', 'not measured')).toBe('2017-2018 only')
    expect(measuredText(false, 'not measured')).toBe('false')
    expect(measuredText(0, 'not measured')).toBe('0')
    expect(measuredText(null, 'not measured')).toBe('not measured')
  })

  it('opens failing and inconclusive details by default and collapses passes; anchors are test-<id>', () => {
    expect(startsOpen('FAIL')).toBe(true)
    expect(startsOpen('INCONCLUSIVE')).toBe(true)
    expect(startsOpen('PASS')).toBe(false)
    expect(startsOpen('NOT_RUN')).toBe(false)
    expect(testAnchor('A1-C3')).toBe('test-A1-C3')
  })
})

// The real results file of the repository (method 0.1.0): the page must tally to what the file holds.
describe('the real validation_results.json', () => {
  const path = new URL('../../../../data/products/validation_results.json', import.meta.url)
  let raw: unknown = null
  try {
    raw = JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    raw = null
  }
  it.skipIf(raw === null)('tallies to the file and groups into the eleven families, with every FAIL entry kept', () => {
    const results = parseValidationResults(raw)
    const counts = countByStatus(results.tests)
    expect(counts.PASS + counts.FAIL + counts.INCONCLUSIVE + counts.NOT_RUN).toBe(results.tests.length)
    const families = groupFamilies(results.tests)
    expect(families.map((f) => f.key)).toEqual(['A1', 'A2', 'B1', 'B2', 'B3', 'C1', 'CTRL', 'D1', 'D2', 'E1', 'S1'])
    expect(families.reduce((n, f) => n + f.tests.length, 0)).toBe(results.tests.length)
    expect(filterTests(results.tests, 'FAIL')).toHaveLength(counts.FAIL)
    // D1 has no family-level entry: its status is the worst of its entries and says so
    expect(families.find((f) => f.key === 'D1')).toMatchObject({ statusFrom: 'worst', status: 'FAIL' })
    expect(families.find((f) => f.key === 'A1')).toMatchObject({ statusFrom: 'entry', status: 'FAIL' })
  })
})
