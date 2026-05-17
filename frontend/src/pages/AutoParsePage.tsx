import { useState, type FormEvent } from 'react';
import {
  Badge,
  Box,
  Flex,
  Heading,
  Input,
  Progress,
  SimpleGrid,
  Spinner,
  Text,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import {
  useAutoParse,
  VacancyCard,
  ParseHistory,
} from '@/features/auto-parse';
import type { ParsingJobStatus } from '@/features/auto-parse';

// ─── Status badge ─────────────────────────────────────────────────────────────

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
      {t(`autoParse.status`)}: {status}
    </Badge>
  );
}

// ─── Search bar ───────────────────────────────────────────────────────────────

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

// ─── Progress bar ─────────────────────────────────────────────────────────────

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

// ─── Vacancy list ─────────────────────────────────────────────────────────────

interface VacancyListProps {
  vacancies: { id: number; vacancy_id: string; url: string; job_title: string; job_text: string; created_at: string }[];
}

function VacancyList({ vacancies }: VacancyListProps) {
  const { t } = useTranslation();

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
    <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
      {vacancies.map((v) => (
        <VacancyCard key={v.id} vacancy={v} />
      ))}
    </SimpleGrid>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AutoParsePage() {
  const { t } = useTranslation();
  const { job, vacancies, isStarting, startParse, loadVacanciesForJob } =
    useAutoParse();

  const isRunning = job?.status === 'running' || job?.status === 'pending';
  const showProgress =
    job !== null && job.status !== 'pending';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
    >
      <Box>
        {/* Page header */}
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

        {/* Search bar */}
        <Box mb={4}>
          <ParseSearchBar
            isDisabled={isRunning}
            isLoading={isStarting}
            onSubmit={startParse}
          />
        </Box>

        {/* Progress bar — visible when running or done */}
        {showProgress && job && (
          <Box mb={6}>
            <ParseProgressBar
              savedCount={job.saved_count}
              totalFound={job.total_found}
              status={job.status}
            />
          </Box>
        )}

        {/* Vacancy list */}
        {(vacancies.length > 0 || job?.status === 'done') && (
          <Box mb={8}>
            <VacancyList vacancies={vacancies} />
          </Box>
        )}

        {/* History */}
        <ParseHistory onSelectJob={loadVacanciesForJob} />
      </Box>
    </motion.div>
  );
}
