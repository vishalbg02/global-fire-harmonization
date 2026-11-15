/** What the help layer shows: the guided tour, the Help sheet, the shortcuts sheet, or nothing. */
export type HelpMode = 'tour' | 'sheet' | 'shortcuts' | null

/** What the keyboard shortcuts and the tour can do in the app. */
export interface HelpActions {
  stepMonth: (delta: -1 | 1) => void
  stepYear: (delta: -1 | 1) => void
  togglePlay: () => void
  toggleGlobe: () => void
  toggleSatellite: () => void
  focusSearch: () => void
}

export interface HelpLayerProps {
  mode: HelpMode
  onMode: (mode: HelpMode) => void
  actions: HelpActions
  /** The map shape now, for the hint shown the first time the globe is chosen. */
  shape: 'flat' | 'globe'
}

/** The guided tour, the Help sheet, the shortcuts sheet and the keyboard shortcuts. */
export function HelpLayer(props: HelpLayerProps) {
  void props
  return null
}
