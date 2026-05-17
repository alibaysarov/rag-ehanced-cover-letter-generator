import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  Flex,
  Spinner,
  Text,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '@/components/ui/GlassCard';
import { autoParseApi } from '../api/auto-parse-client';
import type { ParsingJob, ParsingJobStatus } from '../types';

const AUTO_PARSE_HISTORY_KEY = ['auto-parse', 'history'] as const;

const STATUS_COLOR: Record<ParsingJobStatus, string> = {
  pending: 'yellow',
  running: 'blue',
  done: 'green',
  failed: 'red',
};

interface ParseHistoryProps {
  onSelectJob: (jobId: number) => void;
}

export function ParseHistory({ onSelectJob }: ParseHistoryProps) {
  const { t } = useTranslation();

  const { data: history, isLoading } = useQuery<ParsingJob[], Error>({
    queryKey: AUTO_PARSE_HISTORY_KEY,
    queryFn: () => autoParseApi.getHistory(),
  });

  if (isLoading) {
    return (
      <Flex justify="center" py={6}>
        <Spinner color="aurora.indigo" />
      </Flex>
    );
  }

  if (!history || history.length === 0) {
    return null;
  }

  return (
    <GlassCard padding={0} overflow="hidden">
      <Box px={6} pt={5} pb={3}>
        <Text
          fontFamily="heading"
          fontSize="lg"
          fontWeight={600}
          color="slate.900"
          letterSpacing="-0.01em"
        >
          {t('autoParse.history')}
        </Text>
      </Box>

      <Accordion allowMultiple>
        {history.map((histJob) => (
          <AccordionItem
            key={histJob.id}
            border="none"
            borderTop="1px solid rgba(226,232,240,0.4)"
          >
            <AccordionButton
              px={6}
              py={4}
              _hover={{ bg: 'rgba(99,102,241,0.04)' }}
              onClick={() => onSelectJob(histJob.id)}
            >
              <Flex flex="1" align="center" gap={3} flexWrap="wrap">
                <Badge
                  colorScheme={STATUS_COLOR[histJob.status]}
                  borderRadius="lg"
                  px={2}
                  py={0.5}
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                >
                  {histJob.status}
                </Badge>
                <Text
                  fontSize="sm"
                  fontWeight={500}
                  color="slate.800"
                  flex="1"
                  textAlign="left"
                  noOfLines={1}
                >
                  {histJob.query}
                </Text>
                <Text fontSize="xs" color="slate.500" whiteSpace="nowrap">
                  {histJob.saved_count}/{histJob.total_found}{' '}
                  {t('autoParse.saved')}
                </Text>
              </Flex>
              <AccordionIcon color="slate.400" ml={2} />
            </AccordionButton>

            <AccordionPanel px={6} pb={4}>
              <Text fontSize="xs" color="slate.500" fontFamily="mono">
                ID: {histJob.id} &nbsp;·&nbsp;{' '}
                {new Date(histJob.created_at).toLocaleString()}
                {histJob.finished_at && (
                  <>
                    {' '}
                    &nbsp;→&nbsp;{' '}
                    {new Date(histJob.finished_at).toLocaleString()}
                  </>
                )}
              </Text>
            </AccordionPanel>
          </AccordionItem>
        ))}
      </Accordion>
    </GlassCard>
  );
}
