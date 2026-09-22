import React, { useEffect, useRef, useState } from 'react'
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Stack,
  Text,
  Tooltip,
  useDisclosure,
  useToast,
  VStack,
  Wrap,
  WrapItem,
} from '@chakra-ui/react'
import { AddIcon } from '@chakra-ui/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

import { authApi } from '@/api/client'
import ProjectFormCard, { emptyProject } from '@/components/ProjectFormCard'
import { GradientButton } from '@/components/ui/GradientButton'
import { ListingActionButtons } from '@/components/ui/ListingActionButtons'
import type { ProjectInput } from '@/components/ProjectFormCard'

interface ProjectResponse {
  id: string
  source_id: string
  name: string
  website?: string
  start_month?: number
  start_year?: number
  end_month?: number
  end_year?: number
  currently_working: boolean
  skills: string[]
  achievements: string[]
  technologies: string[]
}

interface ListProjectsResponse {
  projects: ProjectResponse[]
}

interface ApiProjectPayload {
  name: string
  website: string | null
  start_month: number | null
  start_year: number | null
  end_month: number | null
  end_year: number | null
  currently_working: boolean
  skills: string[]
  achievements: string[]
  technologies: string[]
}

const PROJECTS_QUERY_KEY = ['projects'] as const

const useProjects = () =>
  useQuery<ListProjectsResponse, Error>({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: async () => {
      const response = await authApi.get<ListProjectsResponse>('/projects/')
      return response.data
    },
  })

const useSaveProjects = () => {
  const queryClient = useQueryClient()
  return useMutation<
    { saved: number },
    Error,
    { source_id: string; projects: ApiProjectPayload[] }
  >({
    mutationFn: async (payload) => {
      const response = await authApi.post('/projects/save', payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY })
    },
  })
}

const useUpdateProject = () => {
  const queryClient = useQueryClient()
  return useMutation<ProjectResponse, Error, { id: string; data: ApiProjectPayload }>({
    mutationFn: async ({ id, data }) => {
      const response = await authApi.put(`/projects/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY })
    },
  })
}

const useDeleteProject = () => {
  const queryClient = useQueryClient()
  return useMutation<{ success: boolean; message: string }, Error, string>({
    mutationFn: async (id) => {
      const response = await authApi.delete(`/projects/${id}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY })
    },
  })
}

interface DateStrings {
  monthNames: string[]
  currently: string
  dateFrom: string
  dateTo: string
}

const formatDateRange = (p: ProjectResponse, s: DateStrings): string | null => {
  if (!p.start_year && !p.end_year && !p.currently_working) return null
  const start = p.start_year
    ? `${p.start_month ? s.monthNames[p.start_month - 1] + ' ' : ''}${p.start_year}`
    : null
  const end = p.currently_working
    ? s.currently
    : p.end_year
      ? `${p.end_month ? s.monthNames[p.end_month - 1] + ' ' : ''}${p.end_year}`
      : null
  if (start && end) return `${start} — ${end}`
  if (start) return `${s.dateFrom} ${start}`
  if (end) return `${s.dateTo} ${end}`
  return null
}

const cleanProject = (p: ProjectInput): ProjectInput => ({
  name: p.name.trim(),
  website: p.website.trim() || '',
  start_month: p.start_month || '',
  start_year: p.start_year || '',
  end_month: p.currently_working ? '' : p.end_month || '',
  end_year: p.currently_working ? '' : p.end_year || '',
  currently_working: p.currently_working,
  skills: p.skills.map((s) => s.trim()).filter(Boolean),
  achievements: p.achievements.map((s) => s.trim()).filter(Boolean),
  technologies: p.technologies.map((s) => s.trim()).filter(Boolean),
})

const toApiProject = (p: ProjectInput) => ({
  ...cleanProject(p),
  start_month: p.start_month || null,
  start_year: p.start_year || null,
  end_month: p.currently_working ? null : p.end_month || null,
  end_year: p.currently_working ? null : p.end_year || null,
  website: p.website.trim() || null,
})

interface BatchAddModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const BatchAddProjectsModal: React.FC<BatchAddModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { t } = useTranslation()
  const toast = useToast()
  const saveProjects = useSaveProjects()
  const [drafts, setDrafts] = useState<{ id: string; data: ProjectInput }[]>([
    { id: Math.random().toString(36).slice(2), data: emptyProject() },
  ])
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (isOpen) {
      setDrafts([{ id: Math.random().toString(36).slice(2), data: emptyProject() }])
      setErrors({})
    }
  }, [isOpen])

  const updateDraft = (id: string, next: ProjectInput) => {
    setDrafts((prev) => prev.map((d) => (d.id === id ? { ...d, data: next } : d)))
  }

  const removeDraft = (id: string) => {
    setDrafts((prev) => prev.filter((d) => d.id !== id))
  }

  const addDraft = () => {
    setDrafts((prev) => [
      ...prev,
      { id: Math.random().toString(36).slice(2), data: emptyProject() },
    ])
  }

  const handleSubmit = () => {
    const newErrors: Record<string, string> = {}
    drafts.forEach((d) => {
      if (!d.data.name.trim()) {
        newErrors[d.id] = t('projects.nameRequired')
      }
    })
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) {
      return
    }
    if (drafts.length === 0) {
      toast({
        title: t('projects.noProjectsWarning'),
        description: t('projects.addAtLeastOne'),
        status: 'warning',
        duration: 3000,
        isClosable: true,
      })
      return
    }

    const payload = {
      source_id: `manual-${Date.now()}`,
      projects: drafts.map((d) => toApiProject(d.data)),
    }

    saveProjects.mutate(payload, {
      onSuccess: (data) => {
        toast({
          title: t('projects.saveSuccess'),
          description: t('projects.savedCount', { count: data.saved }),
          status: 'success',
          duration: 3000,
          isClosable: true,
        })
        onSuccess()
        onClose()
      },
      onError: (error) => {
        toast({
          title: t('projects.saveError'),
          description: error.message,
          status: 'error',
          duration: 4000,
          isClosable: true,
        })
      },
    })
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{t('projects.addProjectsTitle')}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <AnimatePresence initial={false}>
              {drafts.map((d, idx) => (
                <motion.div
                  key={d.id}
                  initial={{ opacity: 0, y: -10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  transition={{ duration: 0.25 }}
                  style={{ overflow: 'hidden' }}
                >
                  <ProjectFormCard
                    index={idx}
                    value={d.data}
                    nameError={errors[d.id]}
                    onChange={(next) => updateDraft(d.id, next)}
                    onRemove={drafts.length > 1 ? () => removeDraft(d.id) : undefined}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
            <Button
              leftIcon={<AddIcon />}
              onClick={addDraft}
              variant="outline"
              colorScheme="blue"
              alignSelf="flex-start"
            >
              {t('projects.addAnother')}
            </Button>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="danger" mr={3} onClick={onClose}>
            {t('projects.cancel')}
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={saveProjects.isPending}
            loadingText={t('projects.saving')}
          >
            {t('projects.save')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  )
}

interface EditModalProps {
  isOpen: boolean
  onClose: () => void
  project: ProjectResponse | null
}

const EditProjectModal: React.FC<EditModalProps> = ({ isOpen, onClose, project }) => {
  const { t } = useTranslation()
  const toast = useToast()
  const updateProject = useUpdateProject()
  const [draft, setDraft] = useState<ProjectInput>(emptyProject())
  const [nameError, setNameError] = useState<string | undefined>()

  useEffect(() => {
    if (project) {
      setDraft({
        name: project.name,
        website: project.website ?? '',
        start_month: project.start_month ?? '',
        start_year: project.start_year ?? '',
        end_month: project.end_month ?? '',
        end_year: project.end_year ?? '',
        currently_working: project.currently_working ?? false,
        skills: [...project.skills],
        achievements: [...project.achievements],
        technologies: [...project.technologies],
      })
      setNameError(undefined)
    }
  }, [project])

  const handleSubmit = () => {
    if (!draft.name.trim()) {
      setNameError(t('projects.nameRequired'))
      return
    }
    if (!project) return
    updateProject.mutate(
      { id: project.id, data: toApiProject(draft) },
      {
        onSuccess: () => {
          toast({
            title: t('projects.updateSuccess'),
            status: 'success',
            duration: 3000,
            isClosable: true,
          })
          onClose()
        },
        onError: (error) => {
          toast({
            title: t('projects.updateError'),
            description: error.message,
            status: 'error',
            duration: 4000,
            isClosable: true,
          })
        },
      }
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{t('projects.editTitle')}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <ProjectFormCard value={draft} onChange={setDraft} nameError={nameError} />
        </ModalBody>
        <ModalFooter>
          <Button variant="danger" mr={3} onClick={onClose}>
            {t('projects.cancel')}
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={updateProject.isPending}
            loadingText={t('projects.saving')}
          >
            {t('projects.save')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  )
}

const ProjectsPage: React.FC = () => {
  const toast = useToast()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const deleteProject = useDeleteProject()

  const monthNames = t('datePicker.monthsShort', { returnObjects: true }) as string[]
  const dateStrings: DateStrings = {
    monthNames,
    currently: t('projects.currently'),
    dateFrom: t('projects.dateFrom'),
    dateTo: t('projects.dateTo'),
  }

  const { data, isLoading, isError, error } = useProjects()
  const projects = data?.projects ?? []

  const { isOpen: isAddOpen, onOpen: onAddOpen, onClose: onAddClose } = useDisclosure()
  const { isOpen: isEditOpen, onOpen: onEditOpen, onClose: onEditClose } = useDisclosure()
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure()

  const [selected, setSelected] = useState<ProjectResponse | null>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)

  const handleEdit = (p: ProjectResponse) => {
    setSelected(p)
    onEditOpen()
  }

  const handleDelete = (p: ProjectResponse) => {
    setSelected(p)
    onDeleteOpen()
  }

  const confirmDelete = () => {
    if (!selected) return
    deleteProject.mutate(selected.id, {
      onSuccess: () => {
        toast({
          title: t('projects.deleteSuccess'),
          status: 'success',
          duration: 3000,
          isClosable: true,
        })
        onDeleteClose()
      },
      onError: (err) => {
        toast({
          title: t('projects.deleteError'),
          description: err.message,
          status: 'error',
          duration: 4000,
          isClosable: true,
        })
      },
    })
  }

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={7} gap={4} wrap="wrap">
        <Box>
          <Heading size="lg">{t('projects.title')}</Heading>
          <Text color="text.muted" mt={1}>
            {t('projects.subtitle')}
          </Text>
        </Box>
        <HStack spacing={3}>
          <GradientButton
            leftIcon={<AddIcon />}
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: PROJECTS_QUERY_KEY })
              onAddOpen()
            }}
          >
            {t('projects.addProjects')}
          </GradientButton>
        </HStack>
      </Flex>

      {isLoading && (
        <Flex justify="center" py={16}>
          <Spinner />
        </Flex>
      )}

      {isError && (
        <Alert status="error">
          <AlertIcon />
          {t('projects.loadError')} {error?.message || t('projects.unknownError')}
        </Alert>
      )}

      {!isLoading && !isError && projects.length === 0 && (
        <Box bg="surface.raised" p={10} textAlign="center" borderRadius="2xl">
          <Text mb={4} color="text.muted">
            {t('projects.noProjects')}
          </Text>
          <GradientButton leftIcon={<AddIcon />} onClick={onAddOpen}>
            {t('projects.addProjects')}
          </GradientButton>
        </Box>
      )}

      {!isLoading && projects.length > 0 && (
        <Stack spacing={3}>
          <AnimatePresence initial={false}>
            {projects.map((p) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <Box bg="surface.raised" p={5} borderRadius="2xl" boxShadow="sm">
                  <Flex justify="space-between" align="flex-start" gap={4} wrap="wrap">
                    <Box minW={0} flex="1">
                      <Heading size="sm">{p.name || t('projects.noName')}</Heading>
                      {(p.website || formatDateRange(p, dateStrings)) && (
                        <Stack spacing={1} mt={2}>
                          {formatDateRange(p, dateStrings) && (
                            <Text fontSize="sm" color="text.muted">
                              {formatDateRange(p, dateStrings)}
                            </Text>
                          )}
                          {p.website && (
                            <Link
                              href={p.website}
                              isExternal
                              fontSize="sm"
                              color="aurora.indigo"
                              noOfLines={1}
                            >
                              {p.website}
                            </Link>
                          )}
                        </Stack>
                      )}
                      {p.technologies.length > 0 && (
                        <Box mt={3}>
                          <Text fontSize="sm" fontWeight="semibold" mb={1}>
                            {t('projects.technologies')}
                          </Text>
                          <Wrap>
                            {p.technologies.map((tech, i) => (
                              <WrapItem key={i} maxW="100%">
                                <Tooltip
                                  label={tech}
                                  isDisabled={tech.length <= 30}
                                  hasArrow
                                  placement="top"
                                  openDelay={200}
                                >
                                  <Badge
                                    colorScheme="purple"
                                    maxW="200px"
                                    isTruncated
                                    display="block"
                                  >
                                    {tech}
                                  </Badge>
                                </Tooltip>
                              </WrapItem>
                            ))}
                          </Wrap>
                        </Box>
                      )}
                      {p.skills.length > 0 && (
                        <Box mt={3}>
                          <Text fontSize="sm" fontWeight="semibold" mb={1}>
                            {t('projects.skills')}
                          </Text>
                          <Wrap>
                            {p.skills.map((s, i) => (
                              <WrapItem key={i} maxW="100%">
                                <Tooltip
                                  label={s}
                                  isDisabled={s.length <= 30}
                                  hasArrow
                                  placement="top"
                                  openDelay={200}
                                >
                                  <Badge
                                    colorScheme="blue"
                                    maxW="200px"
                                    isTruncated
                                    display="block"
                                  >
                                    {s}
                                  </Badge>
                                </Tooltip>
                              </WrapItem>
                            ))}
                          </Wrap>
                        </Box>
                      )}
                      {p.achievements.length > 0 && (
                        <Box mt={3}>
                          <Text fontSize="sm" fontWeight="semibold" mb={1}>
                            {t('projects.achievements')}
                          </Text>
                          <VStack align="stretch" spacing={1}>
                            {p.achievements.map((a, i) => (
                              <Text key={i} fontSize="sm" color="text.primary">
                                • {a}
                              </Text>
                            ))}
                          </VStack>
                        </Box>
                      )}
                    </Box>
                    <Box flexShrink={0}>
                      <ListingActionButtons
                        editLabel={t('projects.editAriaLabel')}
                        onEdit={() => handleEdit(p)}
                        deleteLabel={t('projects.deleteAriaLabel')}
                        onDelete={() => handleDelete(p)}
                      />
                    </Box>
                  </Flex>
                </Box>
              </motion.div>
            ))}
          </AnimatePresence>
        </Stack>
      )}

      <BatchAddProjectsModal
        isOpen={isAddOpen}
        onClose={onAddClose}
        onSuccess={() => {
          /* invalidation handled in mutation */
        }}
      />
      <EditProjectModal isOpen={isEditOpen} onClose={onEditClose} project={selected} />

      <AlertDialog isOpen={isDeleteOpen} leastDestructiveRef={cancelRef} onClose={onDeleteClose}>
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('projects.deleteTitle')}
            </AlertDialogHeader>
            <AlertDialogBody>
              {t('projects.deleteConfirmBody', { name: selected?.name ?? '' })}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} variant="danger" onClick={onDeleteClose}>
                {t('projects.cancel')}
              </Button>
              <Button
                variant="danger"
                onClick={confirmDelete}
                ml={3}
                isLoading={deleteProject.isPending}
                loadingText={t('projects.deleting')}
              >
                {t('projects.delete')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  )
}

export default ProjectsPage
