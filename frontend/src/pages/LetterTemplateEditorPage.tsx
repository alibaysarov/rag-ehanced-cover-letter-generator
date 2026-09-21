import '@xyflow/react/dist/style.css'
import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  Heading,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Spinner,
  Stack,
  Text,
  useBreakpointValue,
  useDisclosure,
  useToast,
} from '@chakra-ui/react'
import {
  addEdge,
  Background,
  Controls,
  Panel,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from '@xyflow/react'
import axios from 'axios'
import { useEffect, useState } from 'react'
import { IconEye, IconPlus } from '@tabler/icons-react'
import { useBlocker, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { letterConstructorApi } from '@/features/letter-constructor/api'
import { constructorNodeTypes } from '@/features/letter-constructor/components/GraphNodes'
import { constructorEdgeTypes } from '@/features/letter-constructor/components/GraphEdges'
import { PhraseFormModal } from '@/features/letter-constructor/components/PhraseFormModal'
import { apiGraphToFlow, flowGraphToApi } from '@/features/letter-constructor/graphAdapter'
import { useDebouncedValue, usePhrases } from '@/features/letter-constructor/hooks'
import type {
  ConstructorErrorDetail,
  LetterPhrase,
  TemplateCase,
} from '@/features/letter-constructor/types'

const cases: TemplateCase[] = [
  'no_portfolio',
  'relevant_domain',
  'partial_match',
  'no_relevant_projects',
]
const uuid = () => crypto.randomUUID()
const previewTokens: Record<string, string> = {
  '[[job_title]]': 'название вакансии',
  '[[company_name]]': 'название компании',
  '[[matched_technologies]]': 'подходящие технологии',
}
function createsCycle(edges: Edge[], source: string, target: string) {
  if (source === target) return true
  const next = new Map<string, string[]>()
  edges.forEach((edge) => next.set(edge.source, [...(next.get(edge.source) || []), edge.target]))
  const pending = [target],
    seen = new Set<string>()
  while (pending.length) {
    const current = pending.pop()!
    if (current === source) return true
    if (seen.has(current)) continue
    seen.add(current)
    pending.push(...(next.get(current) || []))
  }
  return false
}

function NewPhraseButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <Box
      as="button"
      type="button"
      display="flex"
      flexDirection="column"
      alignItems="center"
      gap={2}
      color="gray.600"
      cursor="pointer"
      onClick={onClick}
      _hover={{ color: 'purple.600' }}
      _focusVisible={{ outline: 'none' }}
      sx={{
        '&:focus-visible > div': {
          borderColor: 'purple.500',
          boxShadow: '0 0 0 3px var(--chakra-colors-purple-100)',
        },
      }}
    >
      <Flex
        w="76px"
        h="76px"
        align="center"
        justify="center"
        border="2px dashed"
        borderColor="gray.300"
        borderRadius="lg"
        bg="white"
        transition="all 0.18s ease"
        sx={{
          'button:hover &': {
            borderColor: 'purple.400',
            bg: 'purple.50',
            transform: 'translateY(-2px)',
            boxShadow: 'md',
          },
          'button:active &': { transform: 'translateY(0)', boxShadow: 'sm' },
        }}
      >
        <IconPlus size={32} stroke={1.8} aria-hidden="true" />
      </Flex>
      <Text fontSize="sm" fontWeight="600">
        {label}
      </Text>
    </Box>
  )
}

export default function LetterTemplateEditorPage() {
  const { id } = useParams(),
    isNew = !id,
    nav = useNavigate(),
    toast = useToast(),
    drawer = useDisclosure(),
    phraseModal = useDisclosure(),
    templatePreviewModal = useDisclosure(),
    templateNameModal = useDisclosure()
  const { t } = useTranslation()
  const mobile = useBreakpointValue({ base: true, lg: false }) ?? false
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]),
    [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [name, setName] = useState(''),
    [templateCase, setCase] = useState<TemplateCase>('no_portfolio'),
    [rootId, setRootId] = useState<string | null>(null)
  const [version, setVersion] = useState<number>(),
    [status, setStatus] = useState('draft'),
    [loading, setLoading] = useState(!isNew),
    [isSaving, setIsSaving] = useState(false),
    [dirty, setDirty] = useState(false),
    [search, setSearch] = useState('')
  const blocker = useBlocker(dirty)
  const [selectedNode, setSelectedNode] = useState<string>(),
    [selectedEdge, setSelectedEdge] = useState<string>(),
    [preview, setPreview] = useState<string>(),
    [parentNodeId, setParentNodeId] = useState<string>(),
    [editingPhrase, setEditingPhrase] = useState<LetterPhrase>(),
    [templateNameDraft, setTemplateNameDraft] = useState('')
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance<Node, Edge>>()
  const phrases = usePhrases({
    q: useDebouncedValue(search) || undefined,
    is_active: true,
    page: 1,
    page_size: 100,
  })
  useEffect(() => {
    if (!id) {
      setNodes([])
      setEdges([])
      setName('')
      setCase('no_portfolio')
      setRootId(null)
      setVersion(undefined)
      setStatus('draft')
      setDirty(false)
      setLoading(false)
      return
    }
    letterConstructorApi
      .template(Number(id))
      .then((template) => {
        const graph = apiGraphToFlow(template)
        setNodes(graph.nodes)
        setEdges(graph.edges)
        setName(template.name)
        setCase(template.case)
        setRootId(template.root_node_id)
        setVersion(template.version)
        setStatus(template.status)
      })
      .catch(() => toast({ status: 'error', title: t('letterConstructor.editor.loadError') }))
      .finally(() => setLoading(false))
  }, [id, setEdges, setNodes, t, toast])
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault()
        event.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', before)
    return () => window.removeEventListener('beforeunload', before)
  }, [dirty])
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    if (window.confirm(t('letterConstructor.editor.unsaved'))) blocker.proceed()
    else blocker.reset()
  }, [blocker, t])
  useEffect(
    () =>
      setNodes((current) =>
        current.map((node) => ({ ...node, data: { ...node.data, isRoot: node.id === rootId } }))
      ),
    [rootId, setNodes]
  )
  const addPhrase = (
    phrase: LetterPhrase,
    parentId?: string,
    position?: { x: number; y: number }
  ) => {
    const newNodeId = uuid()
    const shouldBecomeRoot = nodes.length === 0
    setNodes((current) => {
      const parent = parentId ? current.find((node) => node.id === parentId) : undefined
      return [
        ...current,
        {
          id: newNodeId,
          type: 'phrase',
          position:
            position ??
            (parent
              ? { x: parent.position.x + 320, y: parent.position.y }
              : { x: 80 + current.length * 35, y: 100 + current.length * 35 }),
          data: { phrase, isRoot: false },
        },
      ]
    })
    if (parentId)
      setEdges((current) => [
        ...current,
        {
          id: uuid(),
          source: parentId,
          target: newNodeId,
          data: { branchOrder: current.filter((edge) => edge.source === parentId).length },
        },
      ])
    if (shouldBecomeRoot) setRootId(newNodeId)
    setDirty(true)
  }
  const addProjects = () => {
    if (nodes.some((node) => node.type === 'projects')) return
    const newNodeId = uuid()
    const shouldBecomeRoot = nodes.length === 0
    setNodes((current) => [
      ...current,
      { id: newNodeId, type: 'projects', position: { x: 160, y: 260 }, data: { isRoot: false } },
    ])
    if (shouldBecomeRoot) setRootId(newNodeId)
    setDirty(true)
  }
  const connect = (connection: Connection) => {
    if (
      !connection.source ||
      !connection.target ||
      createsCycle(edges, connection.source, connection.target)
    ) {
      toast({ status: 'warning', title: t('letterConstructor.editor.cycleError') })
      return
    }
    const order = edges.filter((edge) => edge.source === connection.source).length
    setEdges((current) =>
      addEdge({ ...connection, id: uuid(), data: { branchOrder: order } }, current)
    )
    setDirty(true)
  }
  const openChildPhraseModal = (nodeId: string) => {
    setEditingPhrase(undefined)
    setParentNodeId(nodeId)
    phraseModal.onOpen()
  }
  const openPhraseEditor = (nodeId: string) => {
    const node = nodes.find((item) => item.id === nodeId)
    if (node?.type !== 'phrase') return
    setParentNodeId(undefined)
    setEditingPhrase(node.data.phrase as LetterPhrase)
    phraseModal.onOpen()
  }
  const deleteNode = (nodeId: string) => {
    const nextRootId =
      rootId === nodeId
        ? (edges
            .filter((edge) => edge.source === nodeId)
            .sort(
              (first, second) =>
                Number(first.data?.branchOrder ?? 0) - Number(second.data?.branchOrder ?? 0)
            )[0]?.target ?? null)
        : rootId
    setNodes((current) => current.filter((node) => node.id !== nodeId))
    setEdges((current) =>
      current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
    )
    setRootId(nextRootId)
    if (selectedNode === nodeId) setSelectedNode(undefined)
    setDirty(true)
  }
  const deleteEdge = (edgeId: string) => {
    setEdges((current) => current.filter((edge) => edge.id !== edgeId))
    if (selectedEdge === edgeId) setSelectedEdge(undefined)
    setDirty(true)
  }
  const onPhraseDragStart = (event: React.DragEvent, phrase: LetterPhrase) => {
    event.dataTransfer.setData('application/letter-phrase', JSON.stringify(phrase))
    event.dataTransfer.effectAllowed = 'move'
  }
  const onFlowDrop = (event: React.DragEvent) => {
    event.preventDefault()
    const rawPhrase = event.dataTransfer.getData('application/letter-phrase')
    if (!rawPhrase || !flowInstance) return
    try {
      const phrase = JSON.parse(rawPhrase) as LetterPhrase
      addPhrase(
        phrase,
        undefined,
        flowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY })
      )
    } catch {
      /* Ignore data that did not come from the phrase library. */
    }
  }
  const highlight = (detail?: ConstructorErrorDetail) => {
    const errors = detail?.errors || []
    const nodeIds = new Set(
      errors.flatMap((error) =>
        typeof error.node_id === 'string'
          ? [error.node_id]
          : Array.isArray(error.node_ids)
            ? (error.node_ids as string[])
            : []
      )
    )
    const edgeIds = new Set(
      errors.flatMap((error) => (typeof error.edge_id === 'string' ? [error.edge_id] : []))
    )
    setNodes((current) =>
      current.map((node) => ({ ...node, data: { ...node.data, invalid: nodeIds.has(node.id) } }))
    )
    setEdges((current) =>
      current.map((edge) => ({
        ...edge,
        style: edgeIds.has(edge.id) ? { stroke: '#E53E3E', strokeWidth: 3 } : undefined,
      }))
    )
  }
  const save = async (confirm = false, nameOverride?: string) => {
    const templateName = nameOverride ?? name.trim()
    if (!templateName) {
      setTemplateNameDraft(name)
      templateNameModal.onOpen()
      return
    }
    setIsSaving(true)
    const payload = {
      name: templateName,
      case: templateCase,
      ...(isNew ? {} : { version }),
      confirm_without_projects: confirm,
      ...flowGraphToApi(nodes, edges, rootId),
    }
    try {
      const saved = isNew
        ? await letterConstructorApi.createTemplate(payload)
        : await letterConstructorApi.updateTemplate(Number(id), payload)
      setVersion(saved.version)
      setStatus(saved.status)
      setDirty(false)
      highlight()
      if (isNew) nav(`/letter-constructor/templates/${saved.id}/edit`, { replace: true })
    } catch (error) {
      const response = axios.isAxiosError(error) ? error.response : undefined,
        detail = response?.data?.detail as ConstructorErrorDetail | undefined
      highlight(detail)
      if (
        detail?.code === 'projects_node_confirmation_required' &&
        window.confirm(
          t(
            detail.reason === 'missing_projects_node'
              ? 'letterConstructor.editor.missingProjects'
              : 'letterConstructor.editor.partialProjects'
          )
        )
      )
        return save(true, templateName)
      if (response?.status === 409 && detail?.code === 'stale_template_version') {
        if (window.confirm(t('letterConstructor.editor.stale'))) window.location.reload()
        return
      }
      const validationMessage = Array.isArray(response?.data?.detail)
        ? response.data.detail[0]?.msg
        : undefined
      toast({
        status: 'error',
        title: detail?.code || validationMessage || t('letterConstructor.editor.saveError'),
      })
    } finally {
      setIsSaving(false)
    }
  }
  const activate = async () => {
    if (!id || version === undefined) return
    try {
      await letterConstructorApi.activateTemplate(Number(id), version)
      setStatus('active')
    } catch (error) {
      const detail = axios.isAxiosError(error)
        ? (error.response?.data?.detail as ConstructorErrorDetail)
        : undefined
      highlight(detail)
      if (
        detail?.code === 'projects_node_confirmation_required' &&
        window.confirm(t('letterConstructor.editor.partialProjects'))
      ) {
        await letterConstructorApi.activateTemplate(Number(id), version, true)
        setStatus('active')
      }
    }
  }
  const runPreview = async () => {
    if (!id || dirty) return
    const vacancyId = Number(window.prompt(t('letterConstructor.editor.previewVacancy')))
    if (!Number.isInteger(vacancyId)) return
    try {
      const result = await letterConstructorApi.previewTemplate(Number(id), vacancyId)
      setPreview(
        `${result.warning ? `${t('letterConstructor.editor.differentCase')}\n\n` : ''}${result.text}`
      )
    } catch (error) {
      const detail = axios.isAxiosError(error)
        ? (error.response?.data?.detail as ConstructorErrorDetail)
        : undefined
      highlight(detail)
      toast({ status: 'error', title: detail?.code || t('letterConstructor.editor.previewError') })
    }
  }
  const library = (
    <Box w={mobile ? '100%' : '300px'} p={4} overflowY="auto">
      <Heading size="sm" mb={3}>
        {t('letterConstructor.editor.library')}
      </Heading>
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t('letterConstructor.common.search')}
        mb={4}
      />
      <Button
        size="sm"
        w="100%"
        mb={3}
        onClick={addProjects}
        isDisabled={
          templateCase === 'no_portfolio' || nodes.some((node) => node.type === 'projects')
        }
        bg="white"
        color="gray.700"
        border="1px solid"
        borderColor="purple.200"
        _hover={{ bg: 'purple.50', borderColor: 'purple.400' }}
      >
        {t('letterConstructor.editor.addProjects')}
      </Button>
      <Stack>
        {phrases.data?.items.map((phrase) => (
          <Button
            key={phrase.id}
            h="auto"
            py={2}
            whiteSpace="normal"
            onClick={() => addPhrase(phrase)}
            draggable
            onDragStart={(event) => onPhraseDragStart(event, phrase)}
            cursor="grab"
            bg="white"
            color="gray.700"
            border="1px solid"
            borderColor="purple.200"
            boxShadow="sm"
            _hover={{ bg: 'purple.50', borderColor: 'purple.400', boxShadow: 'md' }}
            _active={{ cursor: 'grabbing' }}
          >
            {phrase.text.slice(0, 80)}
          </Button>
        ))}
      </Stack>
    </Box>
  )
  const node = nodes.find((item) => item.id === selectedNode),
    edge = edges.find((item) => item.id === selectedEdge)
  const flowNodes = nodes.map((item) => ({
    ...item,
    data: {
      ...item.data,
      onAddChild: openChildPhraseModal,
      onDelete: deleteNode,
      onEdit: item.type === 'phrase' ? openPhraseEditor : undefined,
      hasOutgoingEdge: edges.some((edge) => edge.source === item.id),
      addChildLabel: t('letterConstructor.editor.newPhrase'),
      deleteLabel: t('letterConstructor.common.delete'),
      editLabel: t('letterConstructor.common.edit'),
    },
  }))
  const flowEdges = edges.map((item) => ({
    ...item,
    type: 'deletable',
    data: { ...item.data, onDelete: deleteEdge },
  }))
  const previewNodeIds = (() => {
    const ordered: string[] = []
    const visited = new Set<string>()
    const visit = (nodeId: string) => {
      if (visited.has(nodeId)) return
      visited.add(nodeId)
      ordered.push(nodeId)
      edges
        .filter((edge) => edge.source === nodeId)
        .sort(
          (first, second) =>
            Number(first.data?.branchOrder ?? 0) - Number(second.data?.branchOrder ?? 0)
        )
        .forEach((edge) => visit(edge.target))
    }
    if (rootId) visit(rootId)
    nodes
      .filter((node) => !visited.has(node.id))
      .sort(
        (first, second) =>
          first.position.x - second.position.x || first.position.y - second.position.y
      )
      .forEach((node) => visit(node.id))
    return ordered
  })()
  const previewNodes = previewNodeIds
    .map((nodeId) => nodes.find((node) => node.id === nodeId))
    .filter((node): node is Node => Boolean(node))
  if (loading) return <Spinner />
  return (
    <Box>
      <Flex gap={3} mb={4} wrap="wrap" align="center">
        <Input
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            setDirty(true)
          }}
          placeholder={t('letterConstructor.editor.name')}
          maxW="320px"
        />
        <Select
          value={templateCase}
          onChange={(event) => {
            setCase(event.target.value as TemplateCase)
            setDirty(true)
          }}
          maxW="260px"
        >
          {cases.map((item) => (
            <option key={item} value={item}>
              {t(`letterConstructor.cases.${item}`)}
            </option>
          ))}
        </Select>
        <Text>
          {status}
          {version ? ` · v${version}` : ''}
        </Text>
        <Button colorScheme="purple" onClick={() => save(false)} isLoading={isSaving}>
          {t('letterConstructor.common.save')}
        </Button>
        <Button
          leftIcon={<IconEye size={18} />}
          variant="outline"
          colorScheme="purple"
          onClick={templatePreviewModal.onOpen}
        >
          Предпросмотр шаблона
        </Button>
        <Button isDisabled={isNew || dirty} onClick={runPreview}>
          {t('letterConstructor.common.preview')}
        </Button>
        <Button isDisabled={isNew || dirty} onClick={activate}>
          {t('letterConstructor.common.activate')}
        </Button>
        {mobile && <Button onClick={drawer.onOpen}>{t('letterConstructor.editor.phrases')}</Button>}
      </Flex>
      {!rootId && nodes.length > 0 && (
        <Alert status="warning" mb={3}>
          <AlertIcon />
          {t('letterConstructor.editor.chooseRoot')}
        </Alert>
      )}
      {preview && (
        <Alert status="info" mb={3}>
          <Box>
            <Button size="xs" float="right" onClick={() => setPreview(undefined)}>
              {t('letterConstructor.common.close')}
            </Button>
            <Text whiteSpace="pre-wrap">{preview}</Text>
          </Box>
        </Alert>
      )}
      <Flex bg="white" borderRadius="xl" overflow="hidden" h="70vh">
        {!mobile && library}
        <Box flex="1">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={constructorNodeTypes}
            edgeTypes={constructorEdgeTypes}
            onInit={setFlowInstance}
            onDragOver={(event) => {
              event.preventDefault()
              event.dataTransfer.dropEffect = 'move'
            }}
            onDrop={onFlowDrop}
            onNodesChange={(changes) => {
              onNodesChange(changes)
              setDirty(true)
            }}
            onEdgesChange={(changes) => {
              onEdgesChange(changes)
              setDirty(true)
            }}
            onConnect={connect}
            onNodeClick={(_, item) => {
              setSelectedNode(item.id)
              setSelectedEdge(undefined)
            }}
            onEdgeClick={(_, item) => {
              setSelectedEdge(item.id)
              setSelectedNode(undefined)
            }}
            onNodeDoubleClick={(_, item) => {
              openPhraseEditor(item.id)
            }}
            fitView
          >
            <Background />
            <Controls />
            <Panel position="top-left">
              <NewPhraseButton
                label={t('letterConstructor.editor.newPhrase')}
                onClick={() => {
                  setEditingPhrase(undefined)
                  setParentNodeId(undefined)
                  phraseModal.onOpen()
                }}
              />
            </Panel>
          </ReactFlow>
        </Box>
        {(node || edge) && (
          <Box w="280px" p={4} borderLeft="1px solid" borderColor="gray.200">
            <Heading size="sm" mb={3}>
              {t('letterConstructor.editor.inspector')}
            </Heading>
            {node && (
              <>
                <Text>
                  {node.type === 'projects'
                    ? '[[projects]]'
                    : (node.data.phrase as LetterPhrase).text}
                </Text>
                <Button
                  size="sm"
                  mt={3}
                  onClick={() => {
                    setRootId(node.id)
                    setDirty(true)
                  }}
                >
                  {t('letterConstructor.editor.makeRoot')}
                </Button>
              </>
            )}
            {edge && (
              <>
                <Text>{t('letterConstructor.editor.branchOrder')}</Text>
                <Input
                  type="number"
                  min={0}
                  value={Number(edge.data?.branchOrder ?? 0)}
                  onChange={(event) => {
                    setEdges((current) =>
                      current.map((item) =>
                        item.id === edge.id
                          ? {
                              ...item,
                              data: { ...item.data, branchOrder: Number(event.target.value) },
                            }
                          : item
                      )
                    )
                    setDirty(true)
                  }}
                />
              </>
            )}
          </Box>
        )}
      </Flex>
      <Drawer isOpen={drawer.isOpen} onClose={drawer.onClose} placement="left">
        <DrawerOverlay />
        <DrawerContent>
          <DrawerHeader>{t('letterConstructor.editor.phrases')}</DrawerHeader>
          <DrawerBody p={0}>{library}</DrawerBody>
        </DrawerContent>
      </Drawer>
      <PhraseFormModal
        isOpen={phraseModal.isOpen}
        phrase={editingPhrase}
        onClose={() => {
          setEditingPhrase(undefined)
          setParentNodeId(undefined)
          phraseModal.onClose()
        }}
        onSaved={async (saved) => {
          if (editingPhrase) {
            setNodes((current) =>
              current.map((node) =>
                node.type === 'phrase' && (node.data.phrase as LetterPhrase).id === saved.id
                  ? { ...node, data: { ...node.data, phrase: saved } }
                  : node
              )
            )
            setDirty(true)
          } else addPhrase(saved, parentNodeId)
          setEditingPhrase(undefined)
          setParentNodeId(undefined)
          await phrases.refetch()
        }}
      />
      <Modal
        isOpen={templatePreviewModal.isOpen}
        onClose={templatePreviewModal.onClose}
        size="2xl"
        isCentered
      >
        <ModalOverlay bg="blackAlpha.500" backdropFilter="blur(4px)" />
        <ModalContent borderRadius="2xl">
          <ModalHeader>Предпросмотр шаблона</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {previewNodes.length === 0 ? (
              <Text color="gray.500">Добавьте ноды, чтобы увидеть текст шаблона.</Text>
            ) : (
              <Stack spacing={4}>
                {previewNodes.map((node, index) => {
                  const text =
                    node.type === 'projects'
                      ? '[[projects]]'
                      : (node.data.phrase as LetterPhrase).text
                  return (
                    <Box key={node.id} borderLeft="3px solid" borderColor="purple.400" pl={4}>
                      <Text fontSize="xs" color="gray.500" mb={1}>
                        {index + 1}.{' '}
                        {node.type === 'projects'
                          ? 'Проекты'
                          : (node.data.phrase as LetterPhrase).type}
                      </Text>
                      <Text whiteSpace="pre-wrap">
                        {text.split(/(\[\[[^\]]+\]\])/g).map((part, partIndex) =>
                          previewTokens[part] ? (
                            <Text
                              as="span"
                              key={partIndex}
                              color="purple.600"
                              fontWeight="semibold"
                            >
                              [{previewTokens[part]}]
                            </Text>
                          ) : part === '[[projects]]' ? (
                            <Text
                              as="span"
                              key={partIndex}
                              color="purple.600"
                              fontWeight="semibold"
                            >
                              [релевантные проекты]
                            </Text>
                          ) : (
                            part
                          )
                        )}
                      </Text>
                    </Box>
                  )
                })}
              </Stack>
            )}
            <Text fontSize="sm" color="gray.500" mt={6}>
              Текст в квадратных скобках будет подставлен автоматически при создании письма.
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button onClick={templatePreviewModal.onClose}>Закрыть</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
      <Modal isOpen={templateNameModal.isOpen} onClose={templateNameModal.onClose} isCentered>
        <ModalOverlay bg="blackAlpha.500" backdropFilter="blur(4px)" />
        <ModalContent borderRadius="2xl">
          <ModalHeader>Название шаблона</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text color="gray.600" mb={3}>
              Укажите название, чтобы сохранить шаблон.
            </Text>
            <Input
              value={templateNameDraft}
              onChange={(event) => setTemplateNameDraft(event.target.value)}
              placeholder="Например, письмо для frontend-разработчика"
              autoFocus
            />
          </ModalBody>
          <ModalFooter gap={3}>
            <Button variant="ghost" onClick={templateNameModal.onClose}>
              Отменить
            </Button>
            <Button
              colorScheme="purple"
              isDisabled={!templateNameDraft.trim()}
              onClick={() => {
                const trimmedName = templateNameDraft.trim()
                setName(trimmedName)
                templateNameModal.onClose()
                void save(false, trimmedName)
              }}
            >
              Сохранить
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  )
}
