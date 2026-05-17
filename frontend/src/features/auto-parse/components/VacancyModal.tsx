import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Button,
  Divider,
  Flex,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Text,
  useClipboard,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { IconCheck, IconCopy, IconExternalLink, IconRefresh, IconSparkles } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { GradientButton } from '@/components/ui/GradientButton';
import { TodayStatsCard, TODAY_SUMMARY_QUERY_KEY } from '@/components/ui/TodayStatsCard';
import { useStreamLetter } from '@/hooks/useStreamLetter';
import { LANGUAGES } from '@/types/letter';
import { autoParseApi } from '../api/auto-parse-client';
import type { AutoParsedJob } from '../types';

// ─── Animations ───────────────────────────────────────────────────────────────

const shimmerKf = keyframes`
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
`;

const blinkKf = keyframes`
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
`;

// ─── Idle orb (same as LetterOutput IdleState) ────────────────────────────────

function IdleOrb() {
  return (
    <Flex direction="column" align="center" justify="center" py={10} gap={5}>
      <Box position="relative" w="160px" h="160px">
        <Box
          position="absolute"
          inset={0}
          borderRadius="full"
          sx={{
            background:
              'radial-gradient(circle at 30% 30%, rgba(99,102,241,0.5) 0%, rgba(217,70,239,0.3) 45%, rgba(6,182,212,0.25) 75%, transparent 100%)',
            filter: 'blur(32px)',
          }}
        />
        <Box
          position="absolute"
          inset="20%"
          borderRadius="full"
          sx={{
            background:
              'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.7) 0%, transparent 70%)',
            filter: 'blur(16px)',
          }}
        />
      </Box>
      <Box textAlign="center">
        <Text fontFamily="heading" fontSize="md" fontWeight={600} color="slate.900" mb={1}>
          Готовы создать письмо
        </Text>
        <Text fontSize="sm" color="slate.500">
          Нажмите «Сгенерировать», чтобы начать
        </Text>
      </Box>
    </Flex>
  );
}

// ─── Shimmer skeleton (same as LetterOutput ParsingState) ─────────────────────

function ShimmerSkeleton() {
  return (
    <Box p={6}>
      <Text fontSize="xs" color="slate.400" mb={5} fontFamily="mono">
        analysing job post…
      </Text>
      {Array.from({ length: 7 }).map((_, i) => (
        <Box
          key={i}
          position="relative"
          overflow="hidden"
          h="13px"
          mb={3.5}
          borderRadius="full"
          bg="rgba(99,102,241,0.08)"
          w={`${70 + ((i * 9) % 28)}%`}
        >
          <Box
            position="absolute"
            inset={0}
            sx={{
              background:
                'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.6) 50%, transparent 100%)',
              animation: `${shimmerKf} 1.6s linear infinite`,
              animationDelay: `${i * 0.13}s`,
            }}
          />
        </Box>
      ))}
    </Box>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function resolveDefaultLang(i18nLang: string): string {
  const code = i18nLang.split('-')[0].toLowerCase();
  const match = LANGUAGES.find((l) => l.code === code);
  return match ? match.label : 'Русский';
}

// ─── Main component ───────────────────────────────────────────────────────────

interface VacancyModalProps {
  vacancy: AutoParsedJob;
  isOpen: boolean;
  onClose: () => void;
  autoGenerate?: boolean;
  onApplied?: (id: number) => void;
}

export function VacancyModal({ vacancy, isOpen, onClose, autoGenerate, onApplied }: VacancyModalProps) {
  const { i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { content, status, streamFromText, reset, preload } = useStreamLetter();
  const { hasCopied, onCopy } = useClipboard(content);
  const [selectedLang, setSelectedLang] = useState(() => resolveDefaultLang(i18n.language));
  const [isApplied, setIsApplied] = useState(vacancy.is_applied);
  const [isMarkingApplied, setIsMarkingApplied] = useState(false);
  const didAutoGenerate = useRef(false);

  useEffect(() => {
    if (isOpen) {
      if (vacancy.cover_letter_text) {
        // Letter was pre-generated via batch — show it immediately
        preload(vacancy.cover_letter_text);
      } else if (autoGenerate && !didAutoGenerate.current) {
        didAutoGenerate.current = true;
        streamFromText({ name: vacancy.job_title, description: vacancy.job_text, lang: selectedLang });
      }
    }
    if (!isOpen) {
      didAutoGenerate.current = false;
      reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, autoGenerate]);

  useEffect(() => {
    setIsApplied(vacancy.is_applied);
  }, [vacancy.is_applied]);

  const handleGenerate = () => {
    streamFromText({ name: vacancy.job_title, description: vacancy.job_text, lang: selectedLang });
  };

  const handleMarkApplied = async () => {
    setIsMarkingApplied(true);
    try {
      await autoParseApi.markApplied(vacancy.id, content || undefined);
      setIsApplied(true);
      onApplied?.(vacancy.id);
      queryClient.invalidateQueries({ queryKey: TODAY_SUMMARY_QUERY_KEY });
    } finally {
      setIsMarkingApplied(false);
    }
  };

  const isGenerating = status === 'parsing' || status === 'streaming';
  const hasContent = content.length > 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay backdropFilter="blur(8px)" bg="rgba(15,23,42,0.4)" />
      <ModalContent
        bg="surface.glass"
        border="1px solid rgba(255,255,255,0.6)"
        borderRadius="3xl"
        boxShadow="inset 0 1px 0 rgba(255,255,255,0.6), 0 24px 64px rgba(79,70,229,0.18)"
        sx={{
          backdropFilter: 'blur(24px) saturate(160%)',
          WebkitBackdropFilter: 'blur(24px) saturate(160%)',
        }}
        mx={4}
      >
        {/* ── Header ── */}
        <ModalHeader
          fontFamily="heading"
          fontWeight={600}
          fontSize="lg"
          color="slate.900"
          letterSpacing="-0.01em"
          pb={2}
          pr={12}
        >
          <Flex align="center" gap={3} flexWrap="wrap" mb={3}>
            <Text>{vacancy.job_title}</Text>
            {isApplied && (
              <Flex
                align="center"
                gap={1}
                bg="green.50"
                border="1px solid"
                borderColor="green.200"
                borderRadius="lg"
                px={2.5}
                py={0.5}
              >
                <IconCheck size={12} stroke={2.5} color="var(--chakra-colors-green-600)" />
                <Text fontSize="xs" fontWeight={600} color="green.600">
                  Откликнулись
                </Text>
              </Flex>
            )}
          </Flex>
          <TodayStatsCard disableSticky />
        </ModalHeader>
        <ModalCloseButton color="slate.500" top={4} right={4} />

        {/* ── Body ── */}
        <ModalBody pb={2}>

          {/* Job description */}
          <Text
            fontSize="xs"
            fontWeight={700}
            color="slate.400"
            textTransform="uppercase"
            letterSpacing="0.08em"
            mb={2}
          >
            Описание вакансии
          </Text>
          <Box
            maxH="240px"
            overflowY="auto"
            bg="rgba(248,250,252,0.7)"
            border="1px solid rgba(226,232,240,0.6)"
            borderRadius="xl"
            p={4}
            mb={5}
            sx={{
              '&::-webkit-scrollbar': { width: '4px' },
              '&::-webkit-scrollbar-track': { background: 'transparent' },
              '&::-webkit-scrollbar-thumb': { background: 'rgba(148,163,184,0.4)', borderRadius: '2px' },
            }}
          >
            <Text fontSize="sm" color="slate.700" whiteSpace="pre-wrap" lineHeight={1.7}>
              {vacancy.job_text}
            </Text>
          </Box>

          <Divider borderColor="rgba(226,232,240,0.6)" mb={5} />

          {/* Letter section — controls row */}
          <Flex align="center" justify="space-between" mb={3} gap={3} flexWrap="wrap">
            <Text
              fontSize="xs"
              fontWeight={700}
              color="slate.400"
              textTransform="uppercase"
              letterSpacing="0.08em"
              flexShrink={0}
            >
              Сопроводительное письмо
            </Text>

            <Flex align="center" gap={2} flexWrap="wrap">
              {/* Language selector */}
              <Select
                size="xs"
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                isDisabled={isGenerating}
                bg="rgba(255,255,255,0.7)"
                border="1px solid rgba(226,232,240,0.8)"
                borderRadius="lg"
                fontSize="xs"
                fontWeight={500}
                color="slate.700"
                width="auto"
                minW="110px"
                _focus={{ borderColor: 'aurora.indigo', boxShadow: '0 0 0 2px rgba(99,102,241,0.15)' }}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.label}>
                    {l.label}
                  </option>
                ))}
              </Select>

              {/* Copy — only when content is ready */}
              {hasContent && !isGenerating && (
                <Button
                  size="xs"
                  height={7}
                  px={3}
                  borderRadius="lg"
                  variant="outline"
                  borderColor={hasCopied ? 'green.300' : 'rgba(226,232,240,0.8)'}
                  color={hasCopied ? 'green.600' : 'slate.600'}
                  bg="rgba(255,255,255,0.7)"
                  fontWeight={500}
                  fontSize="xs"
                  leftIcon={hasCopied ? <IconCheck size={13} stroke={2.5} /> : <IconCopy size={13} stroke={1.8} />}
                  _hover={{ borderColor: 'aurora.indigo', color: 'aurora.indigo', bg: 'rgba(99,102,241,0.06)' }}
                  onClick={onCopy}
                >
                  {hasCopied ? 'Скопировано' : 'Скопировать'}
                </Button>
              )}

              {/* Generate / Regenerate — separated with margin */}
              {!isGenerating && (
                <GradientButton
                  size="xs"
                  onClick={handleGenerate}
                  leftIcon={hasContent ? <IconRefresh size={12} stroke={2} /> : <IconSparkles size={12} stroke={2} />}
                  height={7}
                  px={3}
                  ml={2}
                >
                  {hasContent ? 'Перегенерировать' : 'Сгенерировать'}
                </GradientButton>
              )}
            </Flex>
          </Flex>

          {/* Letter content area */}
          <Box
            bg="rgba(248,250,252,0.7)"
            border="1px solid rgba(226,232,240,0.6)"
            borderRadius="xl"
            overflow="hidden"
          >
            {/* Idle */}
            {status === 'idle' && <IdleOrb />}

            {/* Parsing skeleton */}
            {isGenerating && !hasContent && <ShimmerSkeleton />}

            {/* Streaming / done */}
            {hasContent && (
              <Box p={4}>
                <Text fontSize="sm" color="slate.800" whiteSpace="pre-wrap" lineHeight={1.8}>
                  {content}
                  {isGenerating && (
                    <Box
                      as="span"
                      display="inline-block"
                      w="2px"
                      h="1.1em"
                      bg="aurora.indigo"
                      ml="1px"
                      verticalAlign="text-bottom"
                      sx={{ animation: `${blinkKf} 1s steps(1) infinite` }}
                    />
                  )}
                </Text>
              </Box>
            )}
          </Box>
        </ModalBody>

        {/* ── Footer ── */}
        <ModalFooter gap={3} pt={3}>
          <Box flex="1">
            <Link
              href={vacancy.url}
              isExternal
              display="inline-flex"
              alignItems="center"
              gap={1.5}
              fontSize="sm"
              fontWeight={600}
              color="aurora.indigo"
              _hover={{ textDecoration: 'underline' }}
            >
              Открыть на hh.ru
              <IconExternalLink size={14} stroke={2} />
            </Link>
          </Box>

          {!isApplied && (
            <Button
              size="sm"
              borderRadius="xl"
              colorScheme="green"
              variant="outline"
              isLoading={isMarkingApplied}
              onClick={handleMarkApplied}
              leftIcon={<IconCheck size={14} stroke={2} />}
            >
              Откликнулись?
            </Button>
          )}

          <Button
            size="sm"
            borderRadius="xl"
            variant="ghost"
            color="slate.600"
            onClick={onClose}
            _hover={{ bg: 'rgba(99,102,241,0.08)', color: 'aurora.indigo' }}
          >
            Закрыть
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
