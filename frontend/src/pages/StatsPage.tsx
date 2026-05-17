import { useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Spinner,
  Switch,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useToast,
} from '@chakra-ui/react';
import {
  IconChevronLeft,
  IconChevronRight,
  IconDownload,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { authApi } from '@/api/client';
import { GlassCard } from '@/components/ui/GlassCard';
import { DateRangePicker } from '@/components/ui/DateRangePicker';
import type { DateRange } from '@/components/ui/DateRangePicker';

// ─── Types ───────────────────────────────────────────────────────────────────

interface SentLetter {
  id: number;
  url: string | null;
  job_name: string | null;
  type: 'hh_ru' | 'linkedin' | 'other';
  is_accepted: boolean;
  created_at: string;
}

interface SentLettersPage {
  items: SentLetter[];
  total: number;
  page: number;
  page_size: number;
}

interface SummaryRow {
  date: string;
  hh_ru: number;
  linkedin: number;
  other: number;
  total: number;
}

type TypeFilter = '' | 'hh_ru' | 'linkedin' | 'other';

// ─── Query keys ──────────────────────────────────────────────────────────────

const SENT_LETTERS_KEY = (
  page: number,
  dateFrom: string,
  dateTo: string,
  type: TypeFilter,
) => ['stats', 'sent-letters', page, dateFrom, dateTo, type] as const;

const SUMMARY_KEY = (dateFrom: string, dateTo: string) =>
  ['stats', 'summary', dateFrom, dateTo] as const;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function todayYMD(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function thirtyDaysAgoYMD(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDateRu(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  if (!match) return isoDate;
  return `${match[3]}.${match[2]}.${match[1]}`;
}

const TYPE_LABELS: Record<string, string> = {
  hh_ru: 'hh.ru',
  linkedin: 'LinkedIn',
  other: 'Другие',
};

const TYPE_COLORS: Record<string, string> = {
  hh_ru: 'orange',
  linkedin: 'blue',
  other: 'gray',
};

const PAGE_SIZE = 10;

// ─── Sub-components ──────────────────────────────────────────────────────────

function TypeBadge({ type }: { type: string }) {
  return (
    <Badge
      colorScheme={TYPE_COLORS[type] ?? 'gray'}
      borderRadius="lg"
      px={2}
      py={0.5}
      fontSize="xs"
      fontWeight={600}
      textTransform="none"
    >
      {TYPE_LABELS[type] ?? type}
    </Badge>
  );
}

interface TypeTabsProps {
  value: TypeFilter;
  onChange: (v: TypeFilter) => void;
}

function TypeTabs({ value, onChange }: TypeTabsProps) {
  const options: { value: TypeFilter; label: string }[] = [
    { value: '', label: 'Все' },
    { value: 'hh_ru', label: 'hh.ru' },
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'other', label: 'Другие' },
  ];

  return (
    <Flex
      bg="rgba(255,255,255,0.5)"
      borderRadius="full"
      p={1}
      border="1px solid"
      borderColor="slate.200"
      gap={1}
      w="fit-content"
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Box
            key={o.value}
            as="button"
            type="button"
            onClick={() => onChange(o.value)}
            position="relative"
            px={5}
            py={1.5}
            borderRadius="full"
            fontSize="sm"
            fontWeight={600}
            color={active ? 'white' : 'slate.700'}
            transition="color 200ms ease"
            zIndex={1}
          >
            {active && (
              <motion.div
                layoutId="stats-type-tab-indicator"
                style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: 9999,
                  background:
                    'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                  boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
                  zIndex: -1,
                }}
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            {o.label}
          </Box>
        );
      })}
    </Flex>
  );
}

// ─── Summary table ────────────────────────────────────────────────────────────

function SummaryTable({
  dateFrom,
  dateTo,
}: {
  dateFrom: string;
  dateTo: string;
}) {
  const { data, isLoading, isError } = useQuery<SummaryRow[], Error>({
    queryKey: SUMMARY_KEY(dateFrom, dateTo),
    queryFn: async () => {
      const res = await authApi.get<SummaryRow[]>(
        '/stats/sent-letters/summary',
        { params: { date_from: dateFrom || undefined, date_to: dateTo || undefined } },
      );
      return res.data;
    },
    enabled: true,
  });

  return (
    <GlassCard padding={{ base: 4, md: 6 }}>
      <Text
        fontFamily="heading"
        fontSize="lg"
        fontWeight={600}
        color="slate.900"
        letterSpacing="-0.01em"
        mb={4}
      >
        Сводка по дням
      </Text>

      {isLoading && (
        <Flex justify="center" py={6}>
          <Spinner color="aurora.indigo" />
        </Flex>
      )}

      {isError && (
        <Text fontSize="sm" color="danger.500">
          Не удалось загрузить сводку
        </Text>
      )}

      {data && data.length === 0 && (
        <Text fontSize="sm" color="slate.500">
          Нет данных за выбранный период
        </Text>
      )}

      {data && data.length > 0 && (
        <Box overflowX="auto">
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Дата
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  isNumeric
                  borderColor="rgba(226,232,240,0.5)"
                >
                  hh.ru
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  isNumeric
                  borderColor="rgba(226,232,240,0.5)"
                >
                  LinkedIn
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  isNumeric
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Другие
                </Th>
                <Th
                  color="slate.800"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={700}
                  textTransform="none"
                  letterSpacing="normal"
                  isNumeric
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Итого
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {data.map((row) => (
                <Tr
                  key={row.date}
                  _hover={{ bg: 'rgba(99,102,241,0.04)' }}
                  transition="background 150ms ease"
                >
                  <Td
                    fontSize="sm"
                    color="slate.700"
                    fontFamily="mono"
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {formatDateRu(row.date)}
                  </Td>
                  <Td
                    fontSize="sm"
                    color="slate.600"
                    isNumeric
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {row.hh_ru}
                  </Td>
                  <Td
                    fontSize="sm"
                    color="slate.600"
                    isNumeric
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {row.linkedin}
                  </Td>
                  <Td
                    fontSize="sm"
                    color="slate.600"
                    isNumeric
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {row.other}
                  </Td>
                  <Td
                    fontSize="sm"
                    fontWeight={700}
                    color="slate.900"
                    isNumeric
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {row.total}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
    </GlassCard>
  );
}

// ─── Applications list ────────────────────────────────────────────────────────

function ApplicationsList({
  page,
  dateFrom,
  dateTo,
  typeFilter,
  onPageChange,
}: {
  page: number;
  dateFrom: string;
  dateTo: string;
  typeFilter: TypeFilter;
  onPageChange: (p: number) => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery<SentLettersPage, Error>({
    queryKey: SENT_LETTERS_KEY(page, dateFrom, dateTo, typeFilter),
    queryFn: async () => {
      const res = await authApi.get<SentLettersPage>('/stats/sent-letters', {
        params: {
          page,
          page_size: PAGE_SIZE,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          type: typeFilter || undefined,
        },
      });
      return res.data;
    },
  });

  const toggleMutation = useMutation<
    SentLetter,
    Error,
    { id: number; is_accepted: boolean }
  >({
    mutationFn: async ({ id, is_accepted }) => {
      const res = await authApi.put<SentLetter>(
        `/stats/sent-letters/${id}`,
        { is_accepted },
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['stats', 'sent-letters'],
      });
    },
    onError: (err) => {
      toast({
        title: 'Ошибка обновления',
        description: err.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <GlassCard padding={{ base: 4, md: 6 }}>
      <Text
        fontFamily="heading"
        fontSize="lg"
        fontWeight={600}
        color="slate.900"
        letterSpacing="-0.01em"
        mb={4}
      >
        Отклики
      </Text>

      {isLoading && (
        <Flex justify="center" py={10}>
          <Spinner color="aurora.indigo" />
        </Flex>
      )}

      {isError && (
        <Text fontSize="sm" color="danger.500">
          Не удалось загрузить отклики
        </Text>
      )}

      {data && data.items.length === 0 && (
        <Text fontSize="sm" color="slate.500" py={4}>
          Откликов за выбранный период нет
        </Text>
      )}

      {data && data.items.length > 0 && (
        <Box overflowX="auto">
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Дата
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Тип
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Вакансия
                </Th>
                <Th
                  color="slate.500"
                  fontFamily="body"
                  fontSize="xs"
                  fontWeight={600}
                  textTransform="none"
                  letterSpacing="normal"
                  borderColor="rgba(226,232,240,0.5)"
                >
                  Статус
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {data.items.map((item) => (
                <Tr
                  key={item.id}
                  _hover={{ bg: 'rgba(99,102,241,0.04)' }}
                  transition="background 150ms ease"
                >
                  <Td
                    fontSize="sm"
                    color="slate.600"
                    fontFamily="mono"
                    whiteSpace="nowrap"
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {formatDateRu(item.created_at)}
                  </Td>
                  <Td borderColor="rgba(226,232,240,0.4)">
                    <TypeBadge type={item.type} />
                  </Td>
                  <Td
                    fontSize="sm"
                    color="slate.700"
                    maxW="300px"
                    borderColor="rgba(226,232,240,0.4)"
                  >
                    {item.url ? (
                      <Box
                        as="a"
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        color="aurora.indigo"
                        _hover={{ textDecoration: 'underline' }}
                        display="block"
                        overflow="hidden"
                        textOverflow="ellipsis"
                        whiteSpace="nowrap"
                        maxW="280px"
                      >
                        {item.url}
                      </Box>
                    ) : (
                      <Text
                        overflow="hidden"
                        textOverflow="ellipsis"
                        whiteSpace="nowrap"
                        maxW="280px"
                      >
                        {item.job_name ?? '—'}
                      </Text>
                    )}
                  </Td>
                  <Td borderColor="rgba(226,232,240,0.4)">
                    <Flex align="center" gap={2}>
                      <Switch
                        size="sm"
                        isChecked={item.is_accepted}
                        isDisabled={toggleMutation.isPending}
                        onChange={() =>
                          toggleMutation.mutate({
                            id: item.id,
                            is_accepted: !item.is_accepted,
                          })
                        }
                        colorScheme="green"
                      />
                      <Text
                        fontSize="xs"
                        fontWeight={600}
                        color={item.is_accepted ? 'green.600' : 'slate.400'}
                      >
                        {item.is_accepted ? 'Принято' : 'Ожидает'}
                      </Text>
                    </Flex>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Pagination */}
      {data && data.total > PAGE_SIZE && (
        <Flex align="center" justify="space-between" mt={5} flexWrap="wrap" gap={3}>
          <Text fontSize="sm" color="slate.500">
            Страница{' '}
            <Text as="span" fontWeight={600} color="slate.700">
              {page}
            </Text>{' '}
            из{' '}
            <Text as="span" fontWeight={600} color="slate.700">
              {totalPages}
            </Text>
          </Text>
          <Flex gap={2}>
            <Button
              size="sm"
              borderRadius="xl"
              variant="ghost"
              leftIcon={<IconChevronLeft size={15} stroke={2} />}
              isDisabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              color="slate.600"
              _hover={{ bg: 'rgba(99,102,241,0.08)', color: 'aurora.indigo' }}
            >
              Назад
            </Button>
            <Button
              size="sm"
              borderRadius="xl"
              variant="ghost"
              rightIcon={<IconChevronRight size={15} stroke={2} />}
              isDisabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              color="slate.600"
              _hover={{ bg: 'rgba(99,102,241,0.08)', color: 'aurora.indigo' }}
            >
              Вперёд
            </Button>
          </Flex>
        </Flex>
      )}
    </GlassCard>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const toast = useToast();
  const [dateRange, setDateRange] = useState<DateRange>({
    from: thirtyDaysAgoYMD(),
    to: todayYMD(),
  });
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('');
  const [page, setPage] = useState(1);
  const [isExporting, setIsExporting] = useState(false);

  // Reset to page 1 whenever filters change
  const handleDateChange = (range: DateRange) => {
    setDateRange(range);
    setPage(1);
  };

  const handleTypeChange = (t: TypeFilter) => {
    setTypeFilter(t);
    setPage(1);
  };

  const handleExportCsv = async () => {
    setIsExporting(true);
    try {
      const response = await authApi.get('/stats/sent-letters/export-csv', {
        params: {
          date_from: dateRange.from || undefined,
          date_to: dateRange.to || undefined,
        },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `stats-${dateRange.from ?? 'all'}-${dateRange.to ?? 'all'}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast({
        title: 'Ошибка экспорта',
        description: 'Не удалось скачать CSV',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsExporting(false);
    }
  };

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
            Статистика откликов
          </Heading>
          <Text color="slate.500" fontSize="sm">
            Отслеживайте свои отклики на вакансии и результаты
          </Text>
        </Box>

        {/* Filters bar */}
        <GlassCard padding={{ base: 4, md: 5 }} mb={6}>
          <Flex
            align={{ base: 'flex-start', md: 'center' }}
            justify="space-between"
            flexWrap="wrap"
            gap={4}
          >
            <Flex align="flex-end" gap={4} flexWrap="wrap">
              <DateRangePicker value={dateRange} onChange={handleDateChange} />
              <TypeTabs value={typeFilter} onChange={handleTypeChange} />
            </Flex>

            <Button
              size="sm"
              borderRadius="xl"
              px={4}
              fontWeight={600}
              leftIcon={<IconDownload size={15} stroke={2} />}
              isLoading={isExporting}
              loadingText="Экспорт..."
              onClick={handleExportCsv}
              sx={{
                color: 'white',
                backgroundImage:
                  'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                backgroundSize: '200% 200%',
                backgroundPosition: '0% 0%',
                boxShadow: '0 4px 14px rgba(99,102,241,0.3)',
                transition: 'background-position 400ms ease, box-shadow 200ms ease',
                _hover: {
                  backgroundPosition: '100% 100%',
                  boxShadow: '0 6px 20px rgba(99,102,241,0.4)',
                },
              }}
            >
              Экспорт CSV
            </Button>
          </Flex>
        </GlassCard>

        {/* Summary */}
        <Box mb={6}>
          <SummaryTable dateFrom={dateRange.from} dateTo={dateRange.to} />
        </Box>

        {/* Applications list */}
        <ApplicationsList
          page={page}
          dateFrom={dateRange.from}
          dateTo={dateRange.to}
          typeFilter={typeFilter}
          onPageChange={setPage}
        />
      </Box>
    </motion.div>
  );
}
