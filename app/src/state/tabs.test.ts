import { describe, expect, it } from 'vitest'
import { DEFAULT_TAB, TAB_STORAGE_KEY, initialTab, rememberTab } from './tabs.ts'

/** A storage double: a plain map, or one that throws like a blocked or full storage. */
function memory(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial))
  return {
    data,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
  }
}
const blocked = {
  getItem: (): string | null => {
    throw new Error('SecurityError')
  },
  setItem: (): void => {
    throw new Error('QuotaExceededError')
  },
}

describe('remembered Details tab (T-093)', () => {
  it('opens the tab the user last opened when the link has no tab=', () => {
    expect(initialTab('', memory({ [TAB_STORAGE_KEY]: 'evidence' }))).toBe('evidence')
    expect(initialTab('?area=COUNTRY:IDN&month=2015-09', memory({ [TAB_STORAGE_KEY]: 'analytics' }))).toBe('analytics')
  })

  it('lets the link win over the remembered tab', () => {
    expect(initialTab('?tab=satellites', memory({ [TAB_STORAGE_KEY]: 'evidence' }))).toBe('satellites')
    expect(initialTab('?tab=calendar', memory({ [TAB_STORAGE_KEY]: 'evidence' }))).toBe('calendar')
  })

  it('ignores an invalid tab in the link or in storage', () => {
    expect(initialTab('?tab=nope', memory({ [TAB_STORAGE_KEY]: 'anomalies' }))).toBe('anomalies')
    expect(initialTab('', memory({ [TAB_STORAGE_KEY]: 'nope' }))).toBe(DEFAULT_TAB)
    expect(initialTab('', memory())).toBe(DEFAULT_TAB)
  })

  it('works without storage: blocked, missing or throwing never breaks the page', () => {
    expect(initialTab('', blocked)).toBe(DEFAULT_TAB)
    expect(initialTab('?tab=evidence', blocked)).toBe('evidence')
    expect(initialTab('', null)).toBe(DEFAULT_TAB)
    expect(() => rememberTab('evidence', blocked)).not.toThrow()
    expect(() => rememberTab('evidence', null)).not.toThrow()
  })

  it('remembers the open tab for the next visit', () => {
    const store = memory()
    rememberTab('analytics', store)
    expect(store.data.get(TAB_STORAGE_KEY)).toBe('analytics')
    expect(initialTab('', store)).toBe('analytics')
  })

  it('outside a browser (no window) it uses the link or the default', () => {
    expect(initialTab('?tab=evidence')).toBe('evidence')
    expect(initialTab('')).toBe(DEFAULT_TAB)
    expect(() => rememberTab('evidence')).not.toThrow()
  })
})
