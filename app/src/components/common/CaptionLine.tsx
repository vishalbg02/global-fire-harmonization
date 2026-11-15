import * as UI from '../../content/ui.ts'

/** "Unit: ... Source: ..." under a chart or a table. The method version comes from /api/meta. */
export function CaptionLine({ unit, methodVersion }: { unit: string; methodVersion: string | null }) {
  return (
    <p className="caption-line">
      <span>{`${UI.CAPTION_UNIT}: ${unit}.`}</span> <span>{`${UI.CAPTION_SOURCE(methodVersion)}.`}</span>
    </p>
  )
}
