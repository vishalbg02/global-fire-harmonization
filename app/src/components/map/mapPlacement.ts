/**
 * Where things sit on the map (T-071). Legend bottom-left, scroll hint bottom-right, zoom buttons
 * top-right, loading pill top-centre, pinned cell card top-right BELOW the zoom buttons. The CSS in
 * mapOverlays.css must keep these values (a test reads the CSS and checks them).
 */
export const PLACEMENT = {
  /** Gap to the map edge, in rem. */
  edgeRem: 0.5,
  /** The pinned card starts below the +/- buttons (10 px margin + 2 x 29 px, with air). */
  pinnedTopRem: 5,
  /** Space kept free at the bottom for the legend toggle and the hint, in rem. */
  pinnedBottomRem: 3.5,
} as const

/** Up to this viewport width the card is full width and the legend collapses while it is pinned. */
export const CARD_FULL_WIDTH_PX = 700

/** The cell whose hover tooltip is shown: none for the pinned cell (its card says the same) or over the card. */
export function tooltipCellId(hoveredId: string | null, pinnedId: string | null, overCard: boolean): string | null {
  if (hoveredId === null || overCard) return null
  return hoveredId === pinnedId ? null : hoveredId
}

/** On a small screen the legend folds away while a card is pinned, so neither hides the other. */
export function legendForcedCollapsed(pinned: boolean, viewportWidthPx: number): boolean {
  return pinned && viewportWidthPx <= CARD_FULL_WIDTH_PX
}
