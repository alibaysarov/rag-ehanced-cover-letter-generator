import { Badge, Box, IconButton, Text } from '@chakra-ui/react'
import { IconPlus, IconSettings, IconTrash } from '@tabler/icons-react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { LetterPhrase } from '../types'

type NodeActions = {
  onAddChild?: (nodeId: string) => void
  onDelete?: (nodeId: string) => void
  onEdit?: (nodeId: string) => void
  hasOutgoingEdge?: boolean
  addChildLabel?: string
  deleteLabel?: string
  editLabel?: string
}
export type PhraseFlowNode = Node<
  { phrase: LetterPhrase; isRoot: boolean; invalid?: boolean } & NodeActions,
  'phrase'
>
export type ProjectsFlowNode = Node<
  { isRoot: boolean; invalid?: boolean } & NodeActions,
  'projects'
>
const tokenParts = (text: string) => text.split(/(\[\[[^\]]+\]\])/g)
function NodeControls({ id, data }: { id: string; data: NodeActions }) {
  const stop = (event: React.MouseEvent) => event.stopPropagation()
  return (
    <>
      <Box
        position="absolute"
        top={1}
        right={1}
        zIndex={10}
        display="flex"
        gap={1}
        opacity={0}
        transition="opacity .15s"
        _groupHover={{ opacity: 1 }}
        _focusWithin={{ opacity: 1 }}
      >
        <IconButton
          aria-label={data.deleteLabel ?? 'Delete node'}
          title={data.deleteLabel}
          size="xs"
          colorScheme="red"
          variant="ghost"
          icon={<IconTrash size={16} />}
          onMouseDown={stop}
          onClick={(event) => {
            stop(event)
            data.onDelete?.(id)
          }}
        />
        {data.onEdit && (
          <IconButton
            aria-label={data.editLabel ?? 'Edit node'}
            title={data.editLabel}
            size="xs"
            colorScheme="gray"
            variant="ghost"
            icon={<IconSettings size={16} />}
            onMouseDown={stop}
            onClick={(event) => {
              stop(event)
              data.onEdit?.(id)
            }}
          />
        )}
      </Box>
      {!data.hasOutgoingEdge && (
        <IconButton
          aria-label={data.addChildLabel ?? 'Add node'}
          title={data.addChildLabel}
          position="absolute"
          right="-38px"
          top="50%"
          transform="translateY(-50%)"
          size="xs"
          colorScheme="purple"
          borderRadius="full"
          icon={<IconPlus size={16} />}
          onMouseDown={stop}
          onClick={(event) => {
            stop(event)
            data.onAddChild?.(id)
          }}
        />
      )}
    </>
  )
}
export function PhraseNode({ id, data }: NodeProps<PhraseFlowNode>) {
  return (
    <Box
      role="group"
      position="relative"
      minW="220px"
      maxW="300px"
      bg="surface.raised"
      border="2px solid"
      borderColor={data.invalid ? 'red.400' : data.isRoot ? 'purple.500' : 'gray.200'}
      borderRadius="xl"
      p={3}
      boxShadow="md"
    >
      <Handle type="target" position={Position.Left} />
      <Box>
        <Badge colorScheme="purple">{data.phrase.type}</Badge>
        {data.isRoot && (
          <Badge ml={2} colorScheme="green">
            START
          </Badge>
        )}
      </Box>
      <Text fontSize="sm" mt={2}>
        {tokenParts(data.phrase.text).map((part, i) =>
          part.startsWith('[[') ? (
            <Text as="span" key={i} color="purple.500" fontWeight="bold">
              {part}
            </Text>
          ) : (
            part
          )
        )}
      </Text>
      <Handle type="source" position={Position.Right} />
      <NodeControls id={id} data={data} />
    </Box>
  )
}
export function ProjectsNode({ id, data }: NodeProps<ProjectsFlowNode>) {
  return (
    <Box
      role="group"
      position="relative"
      minW="180px"
      bg="purple.50"
      border="2px solid"
      borderColor={data.invalid ? 'red.400' : data.isRoot ? 'purple.600' : 'purple.300'}
      borderRadius="xl"
      p={4}
    >
      <Handle type="target" position={Position.Left} />
      <Badge colorScheme="purple">[[projects]]</Badge>
      {data.isRoot && (
        <Badge ml={2} colorScheme="green">
          START
        </Badge>
      )}
      <Text mt={2} fontWeight="bold">
        Проекты
      </Text>
      <Handle type="source" position={Position.Right} />
      <NodeControls id={id} data={data} />
    </Box>
  )
}
export const constructorNodeTypes = { phrase: PhraseNode, projects: ProjectsNode }
