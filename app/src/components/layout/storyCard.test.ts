import { describe, expect, it } from 'vitest'
import { STORY_CLOSED_KEY, rememberStoryOpen, storyOpenAtStart } from './storyCard.ts'

function memory(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial))
  return {
    data,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
  }
}
const blocked = {
  getItem: (): string | null => {
    throw new Error('SecurityError')
  },
  setItem: (): void => {
    throw new Error('SecurityError')
  },
  removeItem: (): void => {
    throw new Error('SecurityError')
  },
}

describe('story card memory (T-093)', () => {
  it('is open by default', () => {
    expect(storyOpenAtStart(memory(), false)).toBe(true)
    expect(storyOpenAtStart(null, false)).toBe(true)
  })

  it('stays closed for the rest of the session once closed, and opens again when opened', () => {
    const store = memory()
    rememberStoryOpen(false, store)
    expect(store.data.get(STORY_CLOSED_KEY)).toBe('1')
    expect(storyOpenAtStart(store, false)).toBe(false)
    rememberStoryOpen(true, store)
    expect(store.data.has(STORY_CLOSED_KEY)).toBe(false)
    expect(storyOpenAtStart(store, false)).toBe(true)
  })

  it('starts closed on a phone, as the old "Read more" did', () => {
    expect(storyOpenAtStart(memory(), true)).toBe(false)
  })

  it('never throws when storage is blocked (the card then opens)', () => {
    expect(storyOpenAtStart(blocked, false)).toBe(true)
    expect(() => rememberStoryOpen(false, blocked)).not.toThrow()
    expect(() => rememberStoryOpen(true, null)).not.toThrow()
  })
})
