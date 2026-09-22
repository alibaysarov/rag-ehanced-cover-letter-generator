import { Box, HStack, IconButton, Tooltip } from '@chakra-ui/react'
import { IconPencil, IconTrash } from '@tabler/icons-react'

interface ListingActionButtonsProps {
  editLabel: string
  onEdit: () => void
  deleteLabel: string
  onDelete: () => void
  isDeleteDisabled?: boolean
  deleteTooltip?: string
}

export function ListingActionButtons({
  editLabel,
  onEdit,
  deleteLabel,
  onDelete,
  isDeleteDisabled = false,
  deleteTooltip,
}: ListingActionButtonsProps) {
  return (
    <HStack spacing={1}>
      <Tooltip label={editLabel} hasArrow>
        <IconButton
          aria-label={editLabel}
          icon={<IconPencil size={17} />}
          size="sm"
          variant="ghost"
          color="aurora.indigo"
          cursor="pointer"
          _hover={{ bg: 'blue.50' }}
          onClick={onEdit}
        />
      </Tooltip>
      <Tooltip label={deleteTooltip ?? deleteLabel} hasArrow>
        <Box as="span">
          <IconButton
            aria-label={deleteLabel}
            icon={<IconTrash size={17} />}
            size="sm"
            variant="ghost"
            color="danger.500"
            cursor={isDeleteDisabled ? 'not-allowed' : 'pointer'}
            _hover={{ bg: 'danger.50' }}
            isDisabled={isDeleteDisabled}
            onClick={onDelete}
          />
        </Box>
      </Tooltip>
    </HStack>
  )
}
