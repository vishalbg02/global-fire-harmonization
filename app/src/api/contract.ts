// TypeScript mirror of docs/DATA_CONTRACT.md (contract_version 0.1.1).
// Unknown enum values and missing fields throw ContractError; nothing is coerced.

export const CONTRACT_VERSION = '0.1.1'

export const VERDICTS = [
  'ABOVE_NORMAL',
  'BELOW_NORMAL',
  'WITHIN_NORMAL',
  'CANNOT_DETERMINE',
  'NO_DETECTED_ACTIVITY',
] as const
export type Verdict = (typeof VERDICTS)[number]

export const REASON_CODES = [
  'OUTAGE',
  'INSUFFICIENT_BASELINE',
  'INSUFFICIENT_OVERLAP',
  'WITNESS_DISAGREEMENT',
  'WIDE_INTERVAL',
  'PROVISIONAL_NRT',
  'AQUA_DRIFT_ERA',
  'SINGLE_WITNESS',
  'POOLED_CALIBRATION',
  'DIURNAL_CAVEAT',
  'NOT_HARMONIZED',
] as const
export type ReasonCode = (typeof REASON_CODES)[number]

export const WITNESSES = [
  'AQUA_MODIS',
  'TERRA_MODIS',
  'SNPP_VIIRS',
  'NOAA20_VIIRS',
  'NOAA21_VIIRS',
] as const
export type Witness = (typeof WITNESSES)[number]

export const DATA_LEVELS = ['SP', 'NRT', 'MIXED'] as const
export type DataLevel = (typeof DATA_LEVELS)[number]

/** Layer modes of GET /api/map. */
export const MAP_LAYERS = ['verdict', 'raw', 'harmonized'] as const
export type MapLayer = (typeof MAP_LAYERS)[number]

/** Fields shared by cell_month_harmonized (section 3) and entity_month (section 4). */
export interface HarmonizedFields {
  estimate: number | null
  ci90_low: number | null
  ci90_high: number | null
  sd: number | null
  raw_combined_cell_days: number
  witnesses_used: Witness[]
  n_witnesses: number
  disagreement_scale: number | null
  baseline_median: number | null
  baseline_p25: number | null
  baseline_p75: number | null
  pct_of_normal: number | null
  p_above: number | null
  p_below: number | null
  p_within: number | null
  verdict: Verdict
  reason_codes: ReasonCode[]
  data_level: DataLevel
  method_version: string
}

/** One analysis cell for one month: cell bounds plus cell_month_harmonized fields. */
export interface MapCell extends HarmonizedFields {
  cell_id: string
  lat_min: number
  lat_max: number
  lon_min: number
  lon_max: number
  year: number
  month: number
}

/** A bounding box [west, south, east, north] in degrees (WGS84). */
export type Bbox = readonly [number, number, number, number]

export const ENTITY_TYPES = ['CELL', 'COUNTRY', 'CONTINENT', 'GLOBAL', 'CUSTOM'] as const
export type EntityType = (typeof ENTITY_TYPES)[number]

/** One item of GET /api/entities: a preset area with the bounds of its grid cells. */
export interface EntityItem {
  entity_type: EntityType
  entity_id: string
  entity_name: string
  bbox: Bbox
}

/** The two verdicts GET /api/anomalies can return; the API excludes every other verdict. */
export type AnomalyVerdict = 'ABOVE_NORMAL' | 'BELOW_NORMAL'

/** One item of GET /api/anomalies: an area with a confident above- or below-normal verdict. */
export interface Anomaly {
  entity_type: EntityType
  entity_id: string
  entity_name: string
  verdict: AnomalyVerdict
  p_above: number | null
  p_below: number | null
  pct_of_normal: number | null
}

/**
 * GET /api/evidence: an entity_month record with `raw_by_witness` decoded into an object
 * (witness to raw fire-active cell-days), or null when the record has none.
 */
export interface EntityEvidence extends HarmonizedFields {
  entity_type: EntityType
  entity_id: string
  entity_name: string
  year: number
  month: number
  n_cells: number
  raw_by_witness: Partial<Record<Witness, number>> | null
}

/** One entity for one month (entity_month, section 4). `raw_by_witness` is a JSON string. */
export interface EntityMonth extends HarmonizedFields {
  entity_type: EntityType
  entity_id: string
  entity_name: string
  year: number
  month: number
  n_cells: number
  raw_by_witness: string | null
}

/** The fields of metadata.json that the app uses. */
export interface Metadata {
  contract_version: string
  method_version: string
  synthetic: boolean
  first_month: string
  latest_month: string
  provisional_months: string[]
  citation: string
}

export class ContractError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ContractError'
  }
}

type Rec = Record<string, unknown>

function asRecord(value: unknown, what: string): Rec {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ContractError(`${what}: expected an object`)
  }
  return value as Rec
}

function field(o: Rec, key: string, what: string): unknown {
  if (!(key in o)) throw new ContractError(`${what}: missing field "${key}"`)
  return o[key]
}

function num(o: Rec, key: string, what: string): number {
  const v = field(o, key, what)
  if (typeof v !== 'number' || !Number.isFinite(v)) {
    throw new ContractError(`${what}: "${key}" must be a number`)
  }
  return v
}

function numOrNull(o: Rec, key: string, what: string): number | null {
  const v = field(o, key, what)
  if (v === null) return null
  if (typeof v !== 'number' || !Number.isFinite(v)) {
    throw new ContractError(`${what}: "${key}" must be a number or null`)
  }
  return v
}

function str(o: Rec, key: string, what: string): string {
  const v = field(o, key, what)
  if (typeof v !== 'string') throw new ContractError(`${what}: "${key}" must be a string`)
  return v
}

function oneOf<T extends string>(
  value: unknown,
  allowed: readonly T[],
  key: string,
  what: string,
): T {
  if (typeof value !== 'string' || !(allowed as readonly string[]).includes(value)) {
    throw new ContractError(`${what}: unknown ${key} value ${JSON.stringify(value)}`)
  }
  return value as T
}

function enumList<T extends string>(
  o: Rec,
  key: string,
  allowed: readonly T[],
  what: string,
): T[] {
  const v = field(o, key, what)
  if (!Array.isArray(v)) throw new ContractError(`${what}: "${key}" must be a list`)
  return v.map((item) => oneOf(item, allowed, key, what))
}

function parseHarmonizedFields(o: Rec, what: string): HarmonizedFields {
  return {
    estimate: numOrNull(o, 'estimate', what),
    ci90_low: numOrNull(o, 'ci90_low', what),
    ci90_high: numOrNull(o, 'ci90_high', what),
    sd: numOrNull(o, 'sd', what),
    raw_combined_cell_days: num(o, 'raw_combined_cell_days', what),
    witnesses_used: enumList(o, 'witnesses_used', WITNESSES, what),
    n_witnesses: num(o, 'n_witnesses', what),
    disagreement_scale: numOrNull(o, 'disagreement_scale', what),
    baseline_median: numOrNull(o, 'baseline_median', what),
    baseline_p25: numOrNull(o, 'baseline_p25', what),
    baseline_p75: numOrNull(o, 'baseline_p75', what),
    pct_of_normal: numOrNull(o, 'pct_of_normal', what),
    p_above: numOrNull(o, 'p_above', what),
    p_below: numOrNull(o, 'p_below', what),
    p_within: numOrNull(o, 'p_within', what),
    verdict: oneOf(field(o, 'verdict', what), VERDICTS, 'verdict', what),
    reason_codes: enumList(o, 'reason_codes', REASON_CODES, what),
    data_level: oneOf(field(o, 'data_level', what), DATA_LEVELS, 'data_level', what),
    method_version: str(o, 'method_version', what),
  }
}

export function parseMapCell(raw: unknown): MapCell {
  const what = 'map cell'
  const o = asRecord(raw, what)
  return {
    cell_id: str(o, 'cell_id', what),
    lat_min: num(o, 'lat_min', what),
    lat_max: num(o, 'lat_max', what),
    lon_min: num(o, 'lon_min', what),
    lon_max: num(o, 'lon_max', what),
    year: num(o, 'year', what),
    month: num(o, 'month', what),
    ...parseHarmonizedFields(o, what),
  }
}

export function parseEntityMonth(raw: unknown): EntityMonth {
  const what = 'entity month'
  const o = asRecord(raw, what)
  const rawByWitness = field(o, 'raw_by_witness', what)
  if (rawByWitness !== null && typeof rawByWitness !== 'string') {
    throw new ContractError(`${what}: "raw_by_witness" must be a JSON string or null`)
  }
  return {
    entity_type: oneOf(field(o, 'entity_type', what), ENTITY_TYPES, 'entity_type', what),
    entity_id: str(o, 'entity_id', what),
    entity_name: str(o, 'entity_name', what),
    year: num(o, 'year', what),
    month: num(o, 'month', what),
    n_cells: num(o, 'n_cells', what),
    raw_by_witness: rawByWitness,
    ...parseHarmonizedFields(o, what),
  }
}

/**
 * Decodes a `raw_by_witness` value that is already a plain object (from JSON.parse, never a
 * string) into the contract's witness-keyed map. Shared by `parseEntityEvidence` and by anything
 * that decodes a series record's `raw_by_witness` string itself (T-036, T-037).
 */
export function decodeRawByWitness(
  decoded: unknown,
  what: string,
): Partial<Record<Witness, number>> | null {
  if (decoded === null) return null
  const entries = asRecord(decoded, `${what}: raw_by_witness`)
  const rawByWitness: Partial<Record<Witness, number>> = {}
  for (const [witness, value] of Object.entries(entries)) {
    const key = oneOf(witness, WITNESSES, 'raw_by_witness witness', what)
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new ContractError(`${what}: raw_by_witness "${witness}" must be a number`)
    }
    rawByWitness[key] = value
  }
  return rawByWitness
}

export function parseEntityEvidence(raw: unknown): EntityEvidence {
  const what = 'evidence'
  const o = asRecord(raw, what)
  const rawByWitness = decodeRawByWitness(field(o, 'raw_by_witness', what), what)
  return {
    entity_type: oneOf(field(o, 'entity_type', what), ENTITY_TYPES, 'entity_type', what),
    entity_id: str(o, 'entity_id', what),
    entity_name: str(o, 'entity_name', what),
    year: num(o, 'year', what),
    month: num(o, 'month', what),
    n_cells: num(o, 'n_cells', what),
    raw_by_witness: rawByWitness,
    ...parseHarmonizedFields(o, what),
  }
}

function parseBbox(value: unknown, what: string): Bbox {
  if (!Array.isArray(value) || value.length !== 4 || !value.every((v) => typeof v === 'number' && Number.isFinite(v))) {
    throw new ContractError(`${what}: "bbox" must be [west, south, east, north] numbers`)
  }
  return [value[0], value[1], value[2], value[3]]
}

export function parseEntityItem(raw: unknown): EntityItem {
  const what = 'entity'
  const o = asRecord(raw, what)
  return {
    entity_type: oneOf(field(o, 'entity_type', what), ENTITY_TYPES, 'entity_type', what),
    entity_id: str(o, 'entity_id', what),
    entity_name: str(o, 'entity_name', what),
    bbox: parseBbox(field(o, 'bbox', what), what),
  }
}

export function parseAnomaly(raw: unknown): Anomaly {
  const what = 'anomaly'
  const o = asRecord(raw, what)
  return {
    entity_type: oneOf(field(o, 'entity_type', what), ENTITY_TYPES, 'entity_type', what),
    entity_id: str(o, 'entity_id', what),
    entity_name: str(o, 'entity_name', what),
    // Only these two verdicts are ever ranked; anything else is a contract violation.
    verdict: oneOf(field(o, 'verdict', what), ['ABOVE_NORMAL', 'BELOW_NORMAL'] as const, 'verdict', what),
    p_above: numOrNull(o, 'p_above', what),
    p_below: numOrNull(o, 'p_below', what),
    pct_of_normal: numOrNull(o, 'pct_of_normal', what),
  }
}

export function parseAnomalies(raw: unknown): Anomaly[] {
  if (!Array.isArray(raw)) throw new ContractError('anomalies response: expected a list')
  return raw.map(parseAnomaly)
}

export function parseEntityItems(raw: unknown): EntityItem[] {
  if (!Array.isArray(raw)) throw new ContractError('entities response: expected a list')
  return raw.map(parseEntityItem)
}

/** Parses the JSON string of `EntityMonth.raw_by_witness`, or returns null. Decoding a stored string is not a computation. */
export function parseRawByWitness(
  value: string | null,
  what: string,
): Partial<Record<Witness, number>> | null {
  if (value === null) return null
  let decoded: unknown
  try {
    decoded = JSON.parse(value)
  } catch {
    throw new ContractError(`${what}: "raw_by_witness" is not valid JSON`)
  }
  return decodeRawByWitness(decoded, what)
}

/**
 * An entity_month record (as returned by the series endpoints, with `raw_by_witness` as a JSON
 * string) turned into evidence (with `raw_by_witness` decoded). Used for a custom area, which
 * has no evidence endpoint. Decoding a stored string is not a computation.
 */
export function evidenceFromEntityMonth(record: EntityMonth): EntityEvidence {
  return {
    ...record,
    raw_by_witness: parseRawByWitness(record.raw_by_witness, 'series record'),
  }
}

export function parseEntityMonths(raw: unknown): EntityMonth[] {
  if (!Array.isArray(raw)) throw new ContractError('series response: expected a list of records')
  return raw.map(parseEntityMonth)
}

export function parseMapCells(raw: unknown): MapCell[] {
  if (!Array.isArray(raw)) throw new ContractError('map response: expected a list of cells')
  return raw.map(parseMapCell)
}

const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/

function monthString(o: Rec, key: string, what: string): string {
  const v = str(o, key, what)
  if (!MONTH_RE.test(v)) throw new ContractError(`${what}: "${key}" must be YYYY-MM`)
  return v
}

export function parseMetadata(raw: unknown): Metadata {
  const what = 'metadata'
  const o = asRecord(raw, what)
  const synthetic = field(o, 'synthetic', what)
  if (typeof synthetic !== 'boolean') throw new ContractError(`${what}: "synthetic" must be a boolean`)
  const provisional = field(o, 'provisional_months', what)
  if (!Array.isArray(provisional) || !provisional.every((m) => typeof m === 'string' && MONTH_RE.test(m))) {
    throw new ContractError(`${what}: "provisional_months" must be a list of YYYY-MM`)
  }
  return {
    contract_version: str(o, 'contract_version', what),
    method_version: str(o, 'method_version', what),
    synthetic,
    first_month: monthString(o, 'first_month', what),
    latest_month: monthString(o, 'latest_month', what),
    provisional_months: provisional as string[],
    citation: str(o, 'citation', what),
  }
}

export const TEST_STATUSES = ['PASS', 'FAIL', 'INCONCLUSIVE', 'NOT_RUN'] as const
export type TestStatus = (typeof TEST_STATUSES)[number]

export type MeasuredValue = number | string | boolean | null

/** One test of validation_results.json (contract section 6), exactly as stored. */
export interface ValidationTest {
  test_id: string
  family: string
  title: string
  case: string
  criterion: string
  threshold: string
  measured: Record<string, MeasuredValue>
  status: TestStatus
  notes: string
}

/** GET /api/validation: validation_results.json, served as is. */
export interface ValidationResults {
  contract_version: string
  method_version: string
  generated_at: string
  synthetic: boolean
  tests: ValidationTest[]
}

function parseMeasured(raw: unknown, what: string): Record<string, MeasuredValue> {
  const o = asRecord(raw, `${what} measured`)
  const out: Record<string, MeasuredValue> = {}
  for (const [key, value] of Object.entries(o)) {
    if (
      value !== null &&
      typeof value !== 'number' &&
      typeof value !== 'string' &&
      typeof value !== 'boolean'
    ) {
      throw new ContractError(`${what}: measured "${key}" must be a number, text, true/false or null`)
    }
    out[key] = value
  }
  return out
}

export function parseValidationTest(raw: unknown): ValidationTest {
  const what = 'validation test'
  const o = asRecord(raw, what)
  return {
    test_id: str(o, 'test_id', what),
    family: str(o, 'family', what),
    title: str(o, 'title', what),
    case: str(o, 'case', what),
    criterion: str(o, 'criterion', what),
    threshold: str(o, 'threshold', what),
    measured: parseMeasured(field(o, 'measured', what), what),
    status: oneOf(field(o, 'status', what), TEST_STATUSES, 'status', what),
    notes: str(o, 'notes', what),
  }
}

export function parseValidationResults(raw: unknown): ValidationResults {
  const what = 'validation results'
  const o = asRecord(raw, what)
  const synthetic = field(o, 'synthetic', what)
  if (typeof synthetic !== 'boolean') throw new ContractError(`${what}: "synthetic" must be a boolean`)
  const tests = field(o, 'tests', what)
  if (!Array.isArray(tests)) throw new ContractError(`${what}: "tests" must be a list`)
  return {
    contract_version: str(o, 'contract_version', what),
    method_version: str(o, 'method_version', what),
    generated_at: str(o, 'generated_at', what),
    synthetic,
    tests: tests.map(parseValidationTest),
  }
}
