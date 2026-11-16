import { TOAST_MS } from '../../content/answer.ts'

export interface Toast {
  /** Grows with every toast, so the same message twice is announced twice. */
  id: number
  message: string
}

export interface ToastTimers {
  set: (run: () => void, ms: number) => unknown
  clear: (handle: unknown) => void
}

export interface ToastStore {
  show: (message: string) => void
  hide: () => void
  get: () => Toast | null
  subscribe: (listener: () => void) => () => void
}

const browserTimers: ToastTimers = {
  set: (run, ms) => setTimeout(run, ms),
  clear: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
}

/** One toast at a time: a new one replaces the old one and restarts the clock; each hides itself after `ms`. */
export function createToastStore(timers: ToastTimers = browserTimers, ms: number = TOAST_MS): ToastStore {
  let current: Toast | null = null
  let handle: unknown = null
  let seq = 0
  const listeners = new Set<() => void>()
  const emit = () => listeners.forEach((l) => l())
  const stop = () => {
    if (handle !== null) timers.clear(handle)
    handle = null
  }
  return {
    show(message) {
      stop()
      seq += 1
      current = { id: seq, message }
      handle = timers.set(() => {
        handle = null
        current = null
        emit()
      }, ms)
      emit()
    },
    hide() {
      stop()
      if (current === null) return
      current = null
      emit()
    },
    get: () => current,
    subscribe(listener) {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
  }
}

/** The app's one toast store. */
export const toasts = createToastStore()

/** Shows a short confirmation ("Link copied", "CSV downloaded") in the toast host. */
export const showToast = (message: string) => toasts.show(message)
