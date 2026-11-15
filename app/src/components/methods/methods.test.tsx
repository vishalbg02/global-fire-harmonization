import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ContractError, REASON_CODES, parseValidationResults } from '../../api/contract.ts'
import { methodsHref, pageFromSearch, reasonAnchor } from '../../content/methodsLink.ts'
import { EvidenceBody } from '../evidence/EvidenceBody.tsx'
import { parseEntityEvidence } from '../../api/contract.ts'
import { MethodsPage } from './MethodsPage.tsx'
import { ValidationResultsView } from './ValidationResultsView.tsx'
import { countStatuses } from './validationFormat.ts'

// SYNTHETIC test data. Not NASA observations and not validation results.
const test = (id: string, status: string, extra: object = {}) => ({
  test_id: id,
  family: 'A',
  title: `Title ${id}`,
  case: 'Case',
  criterion: 'Criterion',
  threshold: 'pre-registered at G1',
  measured: { value: 1.5, other: null },
  status,
  notes: '',
  ...extra,
})
const file = (tests: object[], synthetic = false) =>
  parseValidationResults({
    contract_version: '0.1.1',
    method_version: '0.1.0-raw-only',
    generated_at: '2026-11-14T14:44:00Z',
    synthetic,
    tests,
  })

describe('parseValidationResults', () => {
  it('rejects an unknown status instead of coercing it', () => {
    expect(() => file([test('X1', 'PASSED')])).toThrow(ContractError)
    expect(() => file([test('X1', 'pass')])).toThrow(ContractError)
  })

  it('rejects a missing field and a wrongly typed measured value', () => {
    const bad = test('X1', 'PASS') as Record<string, unknown>
    delete bad.criterion
    expect(() => file([bad])).toThrow(ContractError)
    expect(() => file([test('X1', 'PASS', { measured: { v: [1] } })])).toThrow(ContractError)
  })

  it('accepts an empty list of tests', () => {
    expect(file([]).tests).toEqual([])
  })
})

describe('validation results view', () => {
  it('says no test has been run for an empty file, with its metadata, and shows no status', () => {
    const html = renderToString(<ValidationResultsView results={file([])} />)
    expect(html).toContain('No validation test has been run yet')
    expect(html).toContain('2026-11-14T14:44:00Z')
    expect(html).toContain('0.1.0-raw-only')
    expect(html).not.toContain('PASS')
    expect(html).not.toContain('NOT RUN')
  })

  it('shows every status as text plus an icon, in file order, with counts', () => {
    const results = file([test('T1', 'FAIL'), test('T2', 'PASS'), test('T3', 'INCONCLUSIVE'), test('T4', 'NOT_RUN')])
    const html = renderToString(<ValidationResultsView results={results} />)
    for (const label of ['FAIL', 'PASS', 'INCONCLUSIVE', 'NOT RUN']) expect(html).toContain(label)
    expect(html.indexOf('Title T1')).toBeLessThan(html.indexOf('Title T2'))
    expect(html.indexOf('Title T2')).toBeLessThan(html.indexOf('Title T3'))
    expect(html.indexOf('Title T3')).toBeLessThan(html.indexOf('Title T4'))
    expect(countStatuses(results.tests)).toEqual({ PASS: 1, FAIL: 1, INCONCLUSIVE: 1, NOT_RUN: 1 })
    expect(html).toContain('FAIL: 1')
    expect(html).toContain('✖')
  })

  it('never shows PASS for a test that the file does not mark PASS', () => {
    for (const status of ['FAIL', 'INCONCLUSIVE', 'NOT_RUN']) {
      const html = renderToString(<ValidationResultsView results={file([test('T1', status)])} />)
      expect(html).not.toContain('PASS: 1')
      expect(html).not.toMatch(/status-badge[^>]*>(<span[^>]*>[^<]*<\/span>)?PASS/)
      expect(html).toContain('PASS: 0')
    }
  })

  it('shows null as "not measured" and a SYNTHETIC label for a synthetic file', () => {
    const html = renderToString(<ValidationResultsView results={file([test('T1', 'NOT_RUN')], true)} />)
    expect(html).toContain('other: not measured')
    expect(html).toContain('SYNTHETIC')
    expect(renderToString(<ValidationResultsView results={file([test('T1', 'NOT_RUN')])} />)).not.toContain('SYNTHETIC')
  })
})

describe('methods page', () => {
  const page = () => {
    const client = new QueryClient()
    client.setQueryData(['validation'], file([]))
    client.setQueryData(['meta'], { citation: 'We acknowledge the use of FIRMS (SYNTHETIC citation).' })
    return renderToString(
      <QueryClientProvider client={client}>
        <MethodsPage onBack={() => {}} />
      </QueryClientProvider>,
    )
  }

  it('has the sections, every reason code with an anchor, the planned tests apart from the results', () => {
    const html = page()
    for (const code of REASON_CODES) expect(html).toContain(`id="${reasonAnchor(code)}"`)
    expect(html).toContain('NOT_HARMONIZED')
    expect(html.indexOf('Validation results')).toBeLessThan(html.indexOf('Test plan: the pass rules fixed in advance'))
    expect(html).toContain('No validation test has been run yet')
    expect(html).toContain('This is the test plan, not the results')
    expect(html).not.toContain('not run yet)')  // the plan is no longer titled "not run yet": results exist (T-027)
  })

  it('takes the acknowledgement from the metadata and lists the seven dataset DOIs', () => {
    const html = page()
    expect(html).toContain('We acknowledge the use of FIRMS (SYNTHETIC citation).')
    expect(html.match(/href="https:\/\/doi\.org\/10\.5067\//g)?.length).toBe(7)
    expect(html).toContain('Standard (science-quality) products')
    expect(html).toContain('Near-real-time products')
  })

  it('has headings in order: one h2, then h3 sections, with h4 only under an h3', () => {
    const html = page()
    expect(html.match(/<h2/g)?.length).toBe(1)
    const levels = [...html.matchAll(/<h([2-4])/g)].map((m) => Number(m[1]))
    for (let i = 1; i < levels.length; i += 1) expect(levels[i]! - levels[i - 1]!).toBeLessThanOrEqual(1)
  })
})

describe('methods links', () => {
  it('keeps the current selection and adds the page and anchor', () => {
    const href = methodsHref('reason-OUTAGE', { pathname: '/', search: '?area=COUNTRY%3ABRA&month=2026-10' })
    expect(href).toBe('/?area=COUNTRY%3ABRA&month=2026-10&page=methods#reason-OUTAGE')
    expect(pageFromSearch('?area=GLOBAL&page=methods')).toBe('methods')
    expect(pageFromSearch('?page=other')).toBe('map')
    expect(pageFromSearch('')).toBe('map')
  })

  it('gives every reason code in the evidence panel a "Learn more" link to its anchor', () => {
    const record = parseEntityEvidence({
      entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia', year: 2020, month: 7,
      estimate: 10, ci90_low: 8, ci90_high: 12, sd: 1, raw_combined_cell_days: 5, witnesses_used: ['AQUA_MODIS'],
      n_witnesses: 1, disagreement_scale: null, baseline_median: null, baseline_p25: null, baseline_p75: null,
      pct_of_normal: null, p_above: null, p_below: null, p_within: null, verdict: 'CANNOT_DETERMINE',
      reason_codes: ['OUTAGE'], data_level: 'SP', method_version: '0.1.0-combined-no-baseline', n_cells: 3,
      raw_by_witness: { AQUA_MODIS: 5 },
    })
    const html = renderToString(<EvidenceBody record={record} rawByWitness={record.raw_by_witness} contractVersion="0.1.1" />)
    expect(html).toContain('#reason-OUTAGE')
    expect(html).toContain('Learn more')
  })
})
