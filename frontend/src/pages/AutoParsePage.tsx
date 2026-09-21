import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Link,
  Input,
  Progress,
  Switch,
  SimpleGrid,
  Spinner,
  Text,
  useToast,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { IconChevronLeft, IconChevronRight, IconLayoutGrid, IconList, IconSparkles } from '@tabler/icons-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { TodayStatsCard } from '@/components/ui/TodayStatsCard';
import {
  useAutoParse,
  VacancyCard,
  ParseHistory,
} from '@/features/auto-parse';
import type { ParsingJobStatus, AutoParsedJob, GenerationMode } from '@/features/auto-parse';
import type { GenerationState } from '@/features/auto-parse/hooks/useAutoParse';
import {
  DEFAULT_VACANCY_LIMIT,
  isValidVacancyLimit,
  VacancyLimitControl,
} from '@/features/auto-parse/components/VacancyLimitControl';

const STATUS_COLOR: Record<ParsingJobStatus, string> = {
  pending: 'yellow',
  running: 'blue',
  done: 'green',
  failed: 'red',
};

function StatusBadge({ status }: { status: ParsingJobStatus }) {
  const { t } = useTranslation();
  return (
    <Badge
      colorScheme={STATUS_COLOR[status]}
      borderRadius="lg"
      px={2.5}
      py={0.5}
      fontSize="xs"
      fontWeight={600}
      textTransform="none"
    >
      {t('autoParse.status')}: {status}
    </Badge>
  );
}

interface ParseSearchBarProps {
  isDisabled: boolean;
  isLoading: boolean;
  onSubmit: (query: string, mode: GenerationMode, vacancyLimit: number) => void;
}

function ParseSearchBar({ isDisabled, isLoading, onSubmit }: ParseSearchBarProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<GenerationMode>('template');
  const [vacancyLimit, setVacancyLimit] = useState(DEFAULT_VACANCY_LIMIT);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || !isValidVacancyLimit(vacancyLimit)) return;
    onSubmit(trimmed, mode, Number(vacancyLimit));
  };

  return (
    <GlassCard padding={5}>
      <form onSubmit={handleSubmit}>
        <Flex gap={3} align="flex-end" flexWrap="wrap">
          <Box flex="1" minW="220px">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Frontend Developer, Москва"
              isDisabled={isDisabled || isLoading}
              bg="rgba(255,255,255,0.6)"
              border="1px solid rgba(226,232,240,0.8)"
              borderRadius="xl"
              fontSize="sm"
              color="slate.900"
              _placeholder={{ color: 'slate.400' }}
              _focus={{
                borderColor: 'aurora.indigo',
                boxShadow: '0 0 0 3px rgba(99,102,241,0.15)',
                bg: 'rgba(255,255,255,0.8)',
              }}
              _disabled={{ opacity: 0.6, cursor: 'not-allowed' }}
              height={10}
            />
          </Box>
          <GradientButton
            type="submit"
            isDisabled={isDisabled || isLoading || !query.trim() || !isValidVacancyLimit(vacancyLimit)}
            isLoading={isLoading}
            loadingText={t('autoParse.parsing')}
            flexShrink={0}
          >
            {t('autoParse.parse')}
          </GradientButton>
        </Flex>
        <VacancyLimitControl
          value={vacancyLimit}
          onChange={setVacancyLimit}
          isDisabled={isDisabled || isLoading}
        />
        <Flex mt={4} align="center" gap={3} fontSize="sm">
          <Text fontWeight={mode === 'template' ? 700 : 400}>{t('autoParse.templates')}</Text>
          <Switch isChecked={mode === 'ai'} onChange={(e) => setMode(e.target.checked ? 'ai' : 'template')}
            isDisabled={isDisabled || isLoading} aria-label={t('autoParse.useAi')} />
          <Text fontWeight={mode === 'ai' ? 700 : 400}>{t('autoParse.useAi')}</Text>
          <Text color="slate.500" title={t('autoParse.modeHint')}>ⓘ</Text>
        </Flex>
      </form>
    </GlassCard>
  );
}

interface ParseProgressBarProps {
  savedCount: number;
  totalFound: number;
  status: ParsingJobStatus;
}

function ParseProgressBar({ savedCount, totalFound, status }: ParseProgressBarProps) {
  const { t } = useTranslation();
  const percent = totalFound > 0 ? Math.round((savedCount / totalFound) * 100) : 0;

  return (
    <GlassCard padding={5}>
      <Flex align="center" justify="space-between" mb={3} flexWrap="wrap" gap={2}>
        <Flex align="center" gap={2}>
          {status === 'running' && <Spinner size="xs" color="aurora.indigo" />}
          <StatusBadge status={status} />
        </Flex>
        <Text fontSize="sm" fontWeight={600} color="slate.700">
          {savedCount} / {totalFound} {t('autoParse.saved')}
        </Text>
      </Flex>
      <Progress
        value={percent}
        size="sm"
        borderRadius="full"
        sx={{
          '& > div': {
            backgroundImage:
              'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
          },
        }}
        bg="rgba(226,232,240,0.5)"
        hasStripe={status === 'running'}
        isAnimated={status === 'running'}
      />
    </GlassCard>
  );
}

interface GenerationPanelProps {
  genState: GenerationState;
  isStartingGen: boolean;
  onGenerate: () => void;
}

function GenerationPanel({ genState, isStartingGen, onGenerate, mode }: GenerationPanelProps & { mode: GenerationMode }) {
  const isDisabled =
    genState.status === 'running' ||
    isStartingGen ||
    genState.status === 'done';

  const percent =
    genState.total > 0
      ? Math.round((genState.generated / genState.total) * 100)
      : 0;

  return (
    <GlassCard padding={5}>
      <Flex
        align="center"
        justify="space-between"
        mb={genState.status !== 'idle' ? 3 : 0}
        flexWrap="wrap"
        gap={3}
      >
        <Text fontSize="sm" color="slate.600">{mode === 'ai' ? 'Режим: ИИ' : 'Режим: Шаблоны'}</Text>
        <Flex align="center" gap={2}>
          {genState.status === 'running' && <Spinner size="xs" color="purple.500" />}
          {genState.status === 'done' && (
            <Badge
              colorScheme="purple"
              borderRadius="lg"
              px={2.5}
              py={0.5}
              fontSize="xs"
              fontWeight={600}
              textTransform="none"
            >
              Письма готовы
            </Badge>
          )}
          {genState.status === 'running' && (
            <Text fontSize="sm" color="slate.600">
              Генерация: {genState.generated} / {genState.total}
            </Text>
          )}
        </Flex>
        {mode === 'ai' && <GradientButton
          size="sm"
          leftIcon={<IconSparkles size={14} stroke={2} />}
          onClick={onGenerate}
          isDisabled={isDisabled}
          isLoading={isStartingGen}
          loadingText="Запуск..."
          flexShrink={0}
        >
          Сгенерировать сопроводительные
        </GradientButton>}
      </Flex>
      {genState.status === 'running' && (
        <Progress
          value={percent}
          size="sm"
          borderRadius="full"
          sx={{
            '& > div': {
              backgroundImage:
                'linear-gradient(135deg, #8B5CF6 0%, #D946EF 100%)',
            },
          }}
          bg="rgba(226,232,240,0.5)"
          hasStripe
          isAnimated
        />
      )}
    </GlassCard>
  );
}

interface VacancyListProps {
  vacancies: AutoParsedJob[];
  variant: 'compact' | 'hh';
  generationMode: GenerationMode;
  isTemplateGenerationPending: boolean;
}

type PaginationItem = number | 'ellipsis-start' | 'ellipsis-end';

function getPaginationItems(currentPage: number, pageCount: number): PaginationItem[] {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  if (currentPage <= 6) {
    return [1, 2, 3, 4, 5, 6, 'ellipsis-end', pageCount];
  }

  if (currentPage >= pageCount - 5) {
    return [
      1,
      'ellipsis-start',
      ...Array.from({ length: 6 }, (_, index) => pageCount - 5 + index),
    ];
  }

  return [
    1,
    'ellipsis-start',
    currentPage - 1,
    currentPage,
    currentPage + 1,
    'ellipsis-end',
    pageCount,
  ];
}

function VacancyList({ vacancies, variant, generationMode, isTemplateGenerationPending }: VacancyListProps) {
  const { t } = useTranslation();
  const pageSize = 8;
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(vacancies.length / pageSize));
  const paginationItems = useMemo(
    () => getPaginationItems(page, pageCount),
    [page, pageCount],
  );
  const visibleVacancies = useMemo(
    () => vacancies.slice((page - 1) * pageSize, page * pageSize),
    [vacancies, page],
  );

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  if (vacancies.length === 0) {
    return (
      <Flex justify="center" py={10}>
        <Text fontSize="sm" color="slate.400">
          {t('autoParse.noVacancies')}
        </Text>
      </Flex>
    );
  }

  return (
    <>
      <SimpleGrid columns={variant === 'hh' ? 1 : { base: 1, md: 2, lg: 3 }} spacing={4}>
        {visibleVacancies.map((v) => (
          <VacancyCard key={v.id} vacancy={v} variant={variant} generationMode={generationMode} isTemplateGenerationPending={isTemplateGenerationPending} />
        ))}
      </SimpleGrid>
      {pageCount > 1 && (
        <Flex
          as="nav"
          aria-label="Пагинация вакансий"
          mt={6}
          justify="center"
          align="center"
          gap={{ base: 0.5, sm: 1 }}
        >
          <Button
            size="sm"
            variant="ghost"
            minW={8}
            h={8}
            p={0}
            color="slate.500"
            onClick={() => setPage((current) => current - 1)}
            isDisabled={page === 1}
            aria-label="Предыдущая страница"
          >
            <IconChevronLeft size={17} stroke={2} />
          </Button>
          {paginationItems.map((item) =>
            typeof item === 'number' ? (
              <Button
                key={item}
                size="sm"
                variant="ghost"
                minW={8}
                h={8}
                p={0}
                borderRadius="lg"
                fontSize="sm"
                color={item === page ? 'white' : 'slate.600'}
                bg={item === page ? 'aurora.indigo' : 'transparent'}
                boxShadow={item === page ? '0 4px 12px rgba(99, 102, 241, 0.28)' : 'none'}
                _hover={{
                  bg: item === page ? 'aurora.indigo' : 'rgba(255, 255, 255, 0.72)',
                }}
                aria-label={`Страница ${item}`}
                aria-current={item === page ? 'page' : undefined}
                onClick={() => setPage(item)}
              >
                {item}
              </Button>
            ) : (
              <Text
                key={item}
                w={6}
                textAlign="center"
                fontSize="sm"
                color="slate.500"
                aria-hidden="true"
              >
                …
              </Text>
            ),
          )}
          <Button
            size="sm"
            variant="ghost"
            minW={8}
            h={8}
            p={0}
            color="slate.500"
            onClick={() => setPage((current) => current + 1)}
            isDisabled={page === pageCount}
            aria-label="Следующая страница"
          >
            <IconChevronRight size={17} stroke={2} />
          </Button>
        </Flex>
      )}
    </>
  );
}

export default function AutoParsePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const {
    job,
    vacancies,
    isStarting,
    startParse,
    loadVacanciesForJob,
    genState,
    isStartingGen,
    startGeneration,
  } = useAutoParse();
  const [cardVariant, setCardVariant] = useState<'compact' | 'hh'>('hh');
  const handleStartParse = async (query: string, mode: GenerationMode, vacancyLimit: number) => {
    try {
      await startParse(query, mode, vacancyLimit);
      toast({
        title: 'Задача парсинга запущена',
        description: 'Вакансии появятся в списке по мере обработки.',
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: { code?: string; message?: string } } } })?.response?.data?.detail;
      toast({
        title: detail?.message || 'Не удалось запустить парсинг',
        description: detail?.code === 'parsers_empty'
          ? <Link as={RouterLink} to="/search-sites" textDecoration="underline">{t('nav.searchSites')}</Link>
          : undefined,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const showProgress = job !== null;
  const showGeneration = job?.status === 'done' && vacancies.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
    >
      <Box>
        <Box mb={8}>
          <Heading
            fontFamily="heading"
            fontSize="3xl"
            fontWeight={600}
            color="slate.900"
            letterSpacing="-0.02em"
            mb={1}
          >
            {t('autoParse.title')}
          </Heading>
          <Text color="slate.500" fontSize="sm">
            {t('autoParse.subtitle')}
          </Text>
        </Box>

        <TodayStatsCard />

        <Box mb={4}>
          <ParseSearchBar
            isDisabled={isStarting}
            isLoading={isStarting}
            onSubmit={handleStartParse}
          />
        </Box>

        {showProgress && job && (
          <Box mb={4}>
            <ParseProgressBar
              savedCount={job.saved_count}
              totalFound={job.total_found}
              status={job.status}
            />
          </Box>
        )}

        {showGeneration && (
          <Box mb={6}>
            <GenerationPanel
              genState={genState}
              isStartingGen={isStartingGen}
              onGenerate={startGeneration}
              mode={job.generation_mode ?? 'ai'}
            />
          </Box>
        )}

        {(vacancies.length > 0 || job?.status === 'done') && (
          <Box mb={8}>
            {vacancies.length > 0 && (
              <Flex justify="flex-end" mb={3} gap={2}>
                <Button
                  size="sm"
                  variant={cardVariant === 'hh' ? 'solid' : 'outline'}
                  colorScheme="blue"
                  onClick={() => setCardVariant('hh')}
                  aria-label="Вертикальные карточки в стиле HH.ru"
                  title="Вертикальные карточки в стиле HH.ru"
                >
                  <IconList size={20} stroke={2} />
                </Button>

                <Button
                  size="sm"
                  variant={cardVariant === 'compact' ? 'solid' : 'outline'}
                  colorScheme="purple"
                  onClick={() => setCardVariant('compact')}
                  aria-label="Компактные карточки"
                  title="Компактные карточки"
                >
                  <IconLayoutGrid size={18} stroke={2} />
                </Button>
              </Flex>
            )}
            <VacancyList vacancies={vacancies} variant={cardVariant} generationMode={job?.generation_mode ?? 'ai'} isTemplateGenerationPending={job?.generation_mode === 'template' && genState.status !== 'done'} />
          </Box>
        )}

        <ParseHistory onSelectJob={loadVacanciesForJob} />
      </Box>
    </motion.div>
  );
}
