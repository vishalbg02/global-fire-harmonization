import type { Bbox } from '../../api/contract.ts'
import type { Area } from '../../state/selection.ts'
import { CustomAreaForm } from './CustomAreaForm.tsx'
import type { PolygonControls } from './CustomAreaForm.tsx'

interface Props {
  area: Area
  onChooseCustom: (bbox: Bbox) => void
  polygon?: PolygonControls
  drawing: boolean
  onToggleDrawing: () => void
  customMessage: string | null
  customLoading: boolean
}

/**
 * The typed rectangle and polygon forms (the "Draw or type an area" panel). Unchanged behaviour:
 * the same fields, checks and messages as the old area picker's custom section.
 */
export function CustomAreaPanel({ area, onChooseCustom, polygon, drawing, onToggleDrawing, customMessage, customLoading }: Props) {
  return (
    <CustomAreaForm
      key={`${area.entity_type === 'CUSTOM' ? area.entity_id : 'none'}-${polygon?.draft?.seq ?? 0}`}
      initial={area.entity_type === 'CUSTOM' && area.polygon === undefined ? area.bbox : null}
      polygon={
        polygon === undefined
          ? undefined
          : {
              ...polygon,
              initial: polygon.draft?.ring ?? (area.entity_type === 'CUSTOM' ? (area.polygon ?? null) : null),
              drawError: polygon.draft?.error ?? null,
              active: area.entity_type === 'CUSTOM' && area.polygon !== undefined,
            }
      }
      onSubmit={onChooseCustom}
      drawing={drawing}
      onToggleDrawing={onToggleDrawing}
      serverMessage={customMessage}
      loading={customLoading}
    />
  )
}
