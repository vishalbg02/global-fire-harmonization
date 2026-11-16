/**
 * The story card (T-093) is open by default and remembered closed for the rest of the browser session once the user
 * closes it (sessionStorage: nothing leaves the browser, and it is gone when the tab closes). On a phone it starts
 * closed, as the old "Read more" did, so the map stays near the answer. Blocked storage never throws: the card then
 * simply opens again.
 */
export const STORY_CLOSED_KEY = 'gfh.story.closed'
export const STORY_NARROW_QUERY = '(max-width: 640px)'

type SessionStore = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

function sessionStore(): SessionStore | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage
  } catch {
    return null
  }
}

function narrowScreen(): boolean {
  try {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(STORY_NARROW_QUERY).matches
  } catch {
    return false
  }
}

/** Open unless it was closed in this session, or the screen is a phone's. */
export function storyOpenAtStart(store: SessionStore | null = sessionStore(), narrow: boolean = narrowScreen()): boolean {
  if (narrow) return false
  try {
    return store?.getItem(STORY_CLOSED_KEY) !== '1'
  } catch {
    return true
  }
}

/** Remembers the user's choice for this session; a blocked storage is ignored. */
export function rememberStoryOpen(open: boolean, store: SessionStore | null = sessionStore()): void {
  try {
    if (open) store?.removeItem(STORY_CLOSED_KEY)
    else store?.setItem(STORY_CLOSED_KEY, '1')
  } catch {
    // Without storage the card opens again next time; nothing else changes.
  }
}
