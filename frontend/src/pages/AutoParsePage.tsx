import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Input,
  Progress,
  SimpleGrid,
  Spinner,
  Text,
  useToast,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { IconChevronLeft, IconChevronRight, IconLayoutGrid, IconList, IconSparkles } from '@tabler/icons-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { TodayStatsCard } from '@/components/ui/TodayStatsCard';
import {
  useAutoParse,
  VacancyCard,
  ParseHistory,
} from '@/features/auto-parse';
import type { ParsingJobStatus, AutoParsedJob } from '@/features/auto-parse';
import type { GenerationState } from '@/features/auto-parse/hooks/useAutoParse';

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
  onSubmit: (query: string) => void;
}

function ParseSearchBar({ isDisabled, isLoading, onSubmit }: ParseSearchBarProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
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
            isDisabled={isDisabled || isLoading || !query.trim()}
            isLoading={isLoading}
            loadingText={t('autoParse.parsing')}
            flexShrink={0}
          >
            {t('autoParse.parse')}
          </GradientButton>
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

function GenerationPanel({ genState, isStartingGen, onGenerate }: GenerationPanelProps) {
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
        <GradientButton
          size="sm"
          leftIcon={<IconSparkles size={14} stroke={2} />}
          onClick={onGenerate}
          isDisabled={isDisabled}
          isLoading={isStartingGen}
          loadingText="Запуск..."
          flexShrink={0}
        >
          Сгенерировать сопроводительные
        </GradientButton>
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
}

function VacancyList({ vacancies, variant }: VacancyListProps) {
  const { t } = useTranslation();
  const pageSize = 8;
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(vacancies.length / pageSize));
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
          <VacancyCard key={v.id} vacancy={v} variant={variant} />
        ))}
      </SimpleGrid>
      {pageCount > 1 && (
        <Flex mt={6} justify="center" align="center" gap={3}>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((current) => current - 1)}
            isDisabled={page === 1}
            aria-label="Предыдущая страница"
          >
            <IconChevronLeft size={18} />
          </Button>
          <Text fontSize="sm" color="slate.600" fontWeight={600}>
            {page} / {pageCount}
          </Text>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((current) => current + 1)}
            isDisabled={page === pageCount}
            aria-label="Следующая страница"
          >
            <IconChevronRight size={18} />
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
  const [cardVariant, setCardVariant] = useState<'compact' | 'hh'>('compact');
  const handleStartParse = async (query: string) => {
    try {
      await startParse(query);
      toast({
        title: 'Задача парсинга запущена',
        description: 'Вакансии появятся в списке по мере обработки.',
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
    } catch {
      toast({
        title: 'Не удалось запустить парсинг',
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
            />
          </Box>
        )}

        {(vacancies.length > 0 || job?.status === 'done') && (
          <Box mb={8}>
            {vacancies.length > 0 && (
              <Flex justify="flex-end" mb={3} gap={2}>
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
              </Flex>
            )}
            <VacancyList vacancies={vacancies} variant={cardVariant} />
          </Box>
        )}

        <ParseHistory onSelectJob={loadVacanciesForJob} />
      </Box>
    </motion.div>
  );
}
