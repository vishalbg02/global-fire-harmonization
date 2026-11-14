/** Persistent and not dismissable: shown whenever metadata.synthetic is true. */
export function SyntheticBanner({ synthetic }: { synthetic: boolean }) {
  if (!synthetic) return null
  return (
    <div className="synthetic-banner" role="status">
      SYNTHETIC DATA — not NASA observations
    </div>
  )
}
