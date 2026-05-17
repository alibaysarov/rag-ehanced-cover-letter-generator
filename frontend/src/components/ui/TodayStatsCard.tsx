import { Box, Flex, Spinner, Text } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { authApi } from '@/api/client';
import { GlassCard } from './GlassCard';

interface SummaryRow {
  date: string;
  hh_ru: number;
  linkedin: number;
  other: number;
  total: number;
}

function todayYMD(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export const TODAY_SUMMARY_QUERY_KEY = ['stats', 'summary'] as const;

export function TodayStatsCard() {
  const today = todayYMD();
  const cardRef = useRef<HTMLDivElement>(null);
  const [isFixed, setIsFixed] = useState(false);

  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;
    const observer = new IntersectionObserver(
      ([entry]) => setIsFixed(!entry.isIntersecting),
      { threshold: 0, rootMargin: '-1px 0px 0px 0px' }
    );
    observer.observe(card);
    return () => observer.disconnect();
  }, []);

  const { data, isLoading } = useQuery<SummaryRow[], Error>({
    queryKey: [...TODAY_SUMMARY_QUERY_KEY, today, today],
    queryFn: async () => {
      const res = await authApi.get<SummaryRow[]>('/stats/sent-letters/summary', {
        params: { date_from: today, date_to: today },
      });
      return res.data;
    },
  });

  const row = data?.[0];

  const statItems = [
    { label: 'hh.ru', value: row?.hh_ru ?? 0 },
    { label: 'LinkedIn', value: row?.linkedin ?? 0 },
    { label: 'Другие', value: row?.other ?? 0 },
  ];

  const statsContent = (
    <Flex align="center" gap={{ base: 4, md: 8 }} flexWrap="wrap">
      <Text
        fontFamily="heading"
        fontSize="sm"
        fontWeight={600}
        color="slate.700"
        letterSpacing="-0.01em"
        flexShrink={0}
      >
        Откликов за сегодня
      </Text>

      {isLoading ? (
        <Spinner size="sm" color="aurora.indigo" />
      ) : (
        <Flex align="center" gap={{ base: 4, md: 6 }} flexWrap="wrap">
          {statItems.map((item) => (
            <Flex key={item.label} align="center" gap={2}>
              <Text fontSize="xs" color="slate.500" fontWeight={500}>
                {item.label}
              </Text>
              <Text fontSize="sm" fontWeight={700} color="slate.800">
                {item.value}
              </Text>
            </Flex>
          ))}

          <Box w="1px" h="20px" bg="rgba(148,163,184,0.4)" flexShrink={0} />

          <Flex align="center" gap={2}>
            <Text fontSize="xs" color="slate.500" fontWeight={500}>
              Итого
            </Text>
            <Text
              fontSize="md"
              fontWeight={800}
              sx={{
                background:
                  'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              {row?.total ?? 0}
            </Text>
          </Flex>
        </Flex>
      )}
    </Flex>
  );

  return (
    <>
      <Box ref={cardRef} mb={6}>
        <GlassCard padding={{ base: 4, md: '14px 24px' }}>
          {statsContent}
        </GlassCard>
      </Box>

      {/* Fixed bar — slides in from top when original scrolls out of view */}
      <Box
        position="fixed"
        top={0}
        left={{ base: 0, md: '260px' }}
        right={0}
        zIndex={100}
        pointerEvents={isFixed ? 'auto' : 'none'}
        transform={isFixed ? 'translateY(0)' : 'translateY(-110%)'}
        opacity={isFixed ? 1 : 0}
        transition="transform 0.32s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1)"
        px={{ base: 6, md: '48px' }}
        py="14px"
        bg="rgba(245,243,255,0.82)"
        borderBottom="1px solid rgba(255,255,255,0.65)"
        boxShadow="0 4px 24px rgba(99,102,241,0.10), inset 0 1px 0 rgba(255,255,255,0.7)"
        sx={{
          backdropFilter: 'blur(28px) saturate(180%)',
          WebkitBackdropFilter: 'blur(28px) saturate(180%)',
          '@supports not (backdrop-filter: blur(1px))': {
            background: 'rgba(245,243,255,0.96)',
          },
        }}
      >
        {statsContent}
      </Box>
    </>
  );
}
