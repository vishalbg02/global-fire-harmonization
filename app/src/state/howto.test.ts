import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  GLOBE_HINT_KEY,
  HOWTO_KEY,
  isGlobeHintShown,
  isHowToDismissed,
  rememberGlobeHintShown,
  rememberTourDismissed,
  tourOpenAtStart,
} from './howto.ts'

// First-visit help in this browser (T-093). SYNTHETIC: no data are involved.
afterEach(() => vi.unstubAllGlobals())

const stubStorage = (store: Record<string, string>) =>
  vi.stubGlobal('window', {
    localStorage: {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = v
      },
    },
  })

describe('the tour on a first visit', () => {
  it('opens on a bare link in a new browser', () => {
    stubStorage({})
    expect(tourOpenAtStart('')).toBe(true)
  })

  it('never opens for a link with parameters', () => {
    stubStorage({})
    for (const search of ['?month=2015-09', '?area=COUNTRY:IDN&month=2015-09', '?globe=1', '?page=methods']) {
      expect(tourOpenAtStart(search), search).toBe(false)
    }
  })

  it('stays closed once dismissed (Skip, Esc or finished)', () => {
    const store: Record<string, string> = {}
    stubStorage(store)
    rememberTourDismissed()
    expect(store[HOWTO_KEY]).toBe('1')
    expect(isHowToDismissed()).toBe(true)
    expect(tourOpenAtStart('')).toBe(false)
  })

  it('works with storage blocked: nothing throws, and the tour simply shows again', () => {
    vi.stubGlobal('window', {
      get localStorage(): never {
        throw new Error('blocked')
      },
    })
    expect(() => rememberTourDismissed()).not.toThrow()
    expect(tourOpenAtStart('')).toBe(true)
  })
})

describe('the globe hint flag', () => {
  it('is remembered under its own key', () => {
    const store: Record<string, string> = {}
    stubStorage(store)
    expect(isGlobeHintShown()).toBe(false)
    rememberGlobeHintShown()
    expect(store[GLOBE_HINT_KEY]).toBe('1')
    expect(isGlobeHintShown()).toBe(true)
    expect(isHowToDismissed()).toBe(false)
  })

  it('counts as not shown when storage throws on write and on read', () => {
    vi.stubGlobal('window', {
      localStorage: {
        getItem: () => {
          throw new Error('blocked')
        },
        setItem: () => {
          throw new Error('quota')
        },
      },
    })
    expect(() => rememberGlobeHintShown()).not.toThrow()
    expect(isGlobeHintShown()).toBe(false)
  })
})
