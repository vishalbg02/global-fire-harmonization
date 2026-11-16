import { ApiError } from '../../api/client.ts'
import { TOAST_CSV_DOWNLOADED } from '../../content/answer.ts'

export const EXPORT_NOTE =
  'The file holds the stored monthly values with their 90% interval and verdict; read it with the ' +
  'verdict and probabilities, not the estimate alone. Raw hotspot points are not included.'
export const FIRMS_URL = 'https://earthdata.nasa.gov/firms'

/** The message shown when the export fails; the server's own text is used when it sent one. */
export function exportErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.detail !== null) return error.detail
    if (error.status === null) return error.message
    return `The CSV could not be created (${error.message})`
  }
  return 'The CSV could not be created.'
}

/** Saves a blob through a temporary link (the browser's normal download). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export interface ExportDeps<A> {
  download: (area: A, synthetic: boolean) => Promise<{ blob: Blob; filename: string }>
  save: (blob: Blob, filename: string) => void
  /** Confirms a download that was handed to the browser (the toast, "CSV downloaded"). */
  notify: (message: string) => void
}

/** Fetches the CSV, hands it to the browser and confirms it; a failure returns the message to show, with no toast. */
export async function runExport<A>(
  area: A,
  synthetic: boolean,
  deps: ExportDeps<A>,
): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    const file = await deps.download(area, synthetic)
    deps.save(file.blob, file.filename)
  } catch (error) {
    return { ok: false, message: exportErrorMessage(error) }
  }
  deps.notify(TOAST_CSV_DOWNLOADED)
  return { ok: true }
}
