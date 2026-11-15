export interface CopyDeps {
  clipboard?: { writeText: (text: string) => Promise<void> } | undefined
  /** The old route (a hidden text box and `execCommand`); returns whether it worked. */
  legacy?: (text: string) => boolean
}

function legacyCopy(text: string): boolean {
  if (typeof document === 'undefined') return false
  const box = document.createElement('textarea')
  box.value = text
  box.setAttribute('readonly', '')
  box.style.position = 'fixed'
  box.style.opacity = '0'
  document.body.appendChild(box)
  box.select()
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  box.remove()
  return ok
}

/** Copies the text; true when it was copied. Falls back to the old route when the clipboard API is missing or refused. */
export async function copyText(text: string, deps: CopyDeps = {}): Promise<boolean> {
  const clipboard = 'clipboard' in deps ? deps.clipboard : typeof navigator === 'undefined' ? undefined : navigator.clipboard
  const legacy = deps.legacy ?? legacyCopy
  if (clipboard !== undefined) {
    try {
      await clipboard.writeText(text)
      return true
    } catch {
      /* fall through to the old route */
    }
  }
  try {
    return legacy(text)
  } catch {
    return false
  }
}
