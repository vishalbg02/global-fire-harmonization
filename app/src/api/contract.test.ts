import { describe, expect, it } from 'vitest'
import {
  ContractError,
  REASON_CODES,
  VERDICTS,
  parseEntityEvidence,
  parseEntityMonth,
  parseEntityMonths,
  parseMapCell,
  parseMapCells,
  parseMetadata,
} from './contract.ts'

// SYNTHETIC test data. Not NASA observations.
function rawCell(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    cell_id: 'g050_r0123_c0456',
    lat_min: 3,
    lat_max: 3.5,
    lon_min: 46,
    lon_max: 46.5,
    year: 2015,
    month: 9,
    estimate: 12.34,
    ci90_low: 8.1,
    ci90_high: 16.4,
    sd: 2.5,
    raw_combined_cell_days: 20,
    witnesses_used: ['SNPP_VIIRS'],
    n_witnesses: 1,
    disagreement_scale: null,
    baseline_median: 9,
    baseline_p25: 6,
    baseline_p75: 12,
    pct_of_normal: 137,
    p_above: 0.82,
    p_below: 0.02,
    p_within: 0.16,
    verdict: 'ABOVE_NORMAL',
    reason_codes: [],
    data_level: 'SP',
    method_version: 'synthetic-test',
    ...overrides,
  }
}

function rawMeta(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: '0.1.0',
    method_version: 'synthetic-test',
    synthetic: true,
    first_month: '2002-07',
    latest_month: '2026-10',
    provisional_months: ['2026-09', '2026-10'],
    citation: 'SYNTHETIC test citation',
    ...overrides,
  }
}

describe('parseMapCell', () => {
  it('parses a contract-shaped cell', () => {
    const cell = parseMapCell(rawCell())
    expect(cell.verdict).toBe('ABOVE_NORMAL')
    expect(cell.estimate).toBe(12.34)
  })

  it('keeps null as null and a real zero as zero', () => {
    const cell = parseMapCell(rawCell({ estimate: null, pct_of_normal: null, raw_combined_cell_days: 0 }))
    expect(cell.estimate).toBeNull()
    expect(cell.pct_of_normal).toBeNull()
    expect(cell.raw_combined_cell_days).toBe(0)
  })

  it('accepts every verdict and every reason code in the contract', () => {
    for (const verdict of VERDICTS) expect(parseMapCell(rawCell({ verdict })).verdict).toBe(verdict)
    expect(parseMapCell(rawCell({ reason_codes: [...REASON_CODES] })).reason_codes).toHaveLength(REASON_CODES.length)
  })

  it('rejects an unknown verdict instead of coercing it', () => {
    expect(() => parseMapCell(rawCell({ verdict: 'MAYBE_ABOVE' }))).toThrow(ContractError)
  })

  it('rejects an unknown reason code, witness or data level', () => {
    expect(() => parseMapCell(rawCell({ reason_codes: ['NOT_A_CODE'] }))).toThrow(ContractError)
    expect(() => parseMapCell(rawCell({ witnesses_used: ['LANDSAT'] }))).toThrow(ContractError)
    expect(() => parseMapCell(rawCell({ data_level: 'FINAL' }))).toThrow(ContractError)
  })

  it('rejects a missing field and a wrongly typed field', () => {
    const missing = rawCell()
    delete missing.verdict
    expect(() => parseMapCell(missing)).toThrow(/missing field "verdict"/)
    expect(() => parseMapCell(rawCell({ estimate: '12' }))).toThrow(ContractError)
    expect(() => parseMapCell(rawCell({ raw_combined_cell_days: null }))).toThrow(ContractError)
  })

  it('rejects a non-object', () => {
    expect(() => parseMapCell(null)).toThrow(ContractError)
    expect(() => parseMapCell([])).toThrow(ContractError)
  })
})

describe('parseMapCells', () => {
  it('parses a list and rejects a non-list', () => {
    expect(parseMapCells([rawCell(), rawCell({ cell_id: 'g050_r0001_c0002' })])).toHaveLength(2)
    expect(() => parseMapCells({})).toThrow(ContractError)
  })
})

describe('parseMetadata', () => {
  it('parses metadata', () => {
    const meta = parseMetadata(rawMeta())
    expect(meta.synthetic).toBe(true)
    expect(meta.latest_month).toBe('2026-10')
  })

  it('requires synthetic to be a boolean and months to be YYYY-MM', () => {
    expect(() => parseMetadata(rawMeta({ synthetic: 'true' }))).toThrow(ContractError)
    expect(() => parseMetadata(rawMeta({ latest_month: '2026-13' }))).toThrow(ContractError)
    expect(() => parseMetadata(rawMeta({ provisional_months: ['Oct 2026'] }))).toThrow(ContractError)
  })
})

// SYNTHETIC test data. Not NASA observations.
function rawEntityMonth(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const { cell_id: _cellId, lat_min: _a, lat_max: _b, lon_min: _c, lon_max: _d, ...harmonized } = rawCell()
  return {
    ...harmonized,
    entity_type: 'COUNTRY',
    entity_id: 'IDN',
    entity_name: 'Indonesia',
    n_cells: 10,
    raw_by_witness: '{"AQUA_MODIS": 5}',
    ...overrides,
  }
}

describe('parseEntityMonth', () => {
  it('parses a contract-shaped record and keeps raw_by_witness as a string', () => {
    const r = parseEntityMonth(rawEntityMonth())
    expect(r.entity_id).toBe('IDN')
    expect(r.raw_by_witness).toBe('{"AQUA_MODIS": 5}')
    expect(r.verdict).toBe('ABOVE_NORMAL')
  })

  it('keeps null as null and a real zero as zero', () => {
    const r = parseEntityMonth(
      rawEntityMonth({ pct_of_normal: null, estimate: 0, raw_by_witness: null, raw_combined_cell_days: 0 }),
    )
    expect(r.pct_of_normal).toBeNull()
    expect(r.estimate).toBe(0)
    expect(r.raw_by_witness).toBeNull()
  })

  it('rejects an unknown entity type or verdict, a missing field and a non-string raw_by_witness', () => {
    expect(() => parseEntityMonth(rawEntityMonth({ entity_type: 'PLANET' }))).toThrow(ContractError)
    expect(() => parseEntityMonth(rawEntityMonth({ verdict: 'MAYBE' }))).toThrow(ContractError)
    const missing = rawEntityMonth()
    delete missing.n_cells
    expect(() => parseEntityMonth(missing)).toThrow(/missing field "n_cells"/)
    expect(() => parseEntityMonth(rawEntityMonth({ raw_by_witness: { AQUA_MODIS: 5 } }))).toThrow(ContractError)
  })

  it('parses a list and rejects a non-list', () => {
    expect(parseEntityMonths([rawEntityMonth(), rawEntityMonth({ month: 10 })])).toHaveLength(2)
    expect(() => parseEntityMonths({})).toThrow(ContractError)
  })
})


describe('parseEntityEvidence', () => {
  const evidence = (overrides: Record<string, unknown> = {}) =>
    rawEntityMonth({ raw_by_witness: { AQUA_MODIS: 5, SNPP_VIIRS: 0 }, ...overrides })

  it('parses a record with raw_by_witness decoded into an object and keeps a real zero', () => {
    const r = parseEntityEvidence(evidence())
    expect(r.raw_by_witness).toEqual({ AQUA_MODIS: 5, SNPP_VIIRS: 0 })
    expect(r.verdict).toBe('ABOVE_NORMAL')
  })

  it('keeps a null raw_by_witness as null', () => {
    expect(parseEntityEvidence(evidence({ raw_by_witness: null })).raw_by_witness).toBeNull()
  })

  it('rejects an unknown witness, a non-numeric contribution and a string raw_by_witness', () => {
    expect(() => parseEntityEvidence(evidence({ raw_by_witness: { LANDSAT: 3 } }))).toThrow(ContractError)
    expect(() => parseEntityEvidence(evidence({ raw_by_witness: { AQUA_MODIS: 'many' } }))).toThrow(ContractError)
    expect(() => parseEntityEvidence(evidence({ raw_by_witness: '{"AQUA_MODIS": 5}' }))).toThrow(ContractError)
  })

  it('rejects an unknown verdict and a missing field', () => {
    expect(() => parseEntityEvidence(evidence({ verdict: 'MAYBE' }))).toThrow(ContractError)
    const missing = evidence()
    delete missing.pct_of_normal
    expect(() => parseEntityEvidence(missing)).toThrow(/missing field "pct_of_normal"/)
  })
})
