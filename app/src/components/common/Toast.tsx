import { useSyncExternalStore } from 'react'
import { toasts } from './toastStore.ts'
import type { ToastStore } from './toastStore.ts'
import './toast.css'

/**
 * The one toast host of the page. The live region is always in the page (a region added at the same time as its text
 * is often not read out); the toast inside it changes. Placed over the map, never over the answer panel.
 */
export function ToastHost({ store = toasts }: { store?: ToastStore }) {
  const toast = useSyncExternalStore(store.subscribe, store.get, () => null)
  return (
    <div className="toast-host" role="status" aria-live="polite" aria-atomic="true">
      {toast !== null && (
        <p key={toast.id} className="toast">
          {toast.message}
        </p>
      )}
    </div>
  )
}
