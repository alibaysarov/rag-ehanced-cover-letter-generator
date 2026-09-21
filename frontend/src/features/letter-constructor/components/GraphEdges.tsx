import { IconUnlink } from '@tabler/icons-react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'

type DeletableEdgeData = { onDelete?: (edgeId: string) => void }

export function DeletableEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })
  const edgeData = data as DeletableEdgeData | undefined

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <button
          type="button"
          aria-label="Remove connection"
          title="Remove connection"
          className="nodrag nopan"
          onMouseDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation()
            edgeData?.onDelete?.(id)
          }}
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
            display: 'grid',
            placeItems: 'center',
            width: 24,
            height: 24,
            padding: 0,
            border: '1px solid #d6bcfa',
            borderRadius: '999px',
            background: 'white',
            color: '#805ad5',
            cursor: 'pointer',
            boxShadow: '0 1px 4px rgba(0,0,0,.16)',
          }}
        >
          <IconUnlink size={14} />
        </button>
      </EdgeLabelRenderer>
    </>
  )
}

export const constructorEdgeTypes = { deletable: DeletableEdge }
