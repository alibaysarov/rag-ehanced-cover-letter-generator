import { useMemo, useState } from 'react';
import {
  Box,
  Flex,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import {
  IconCheck,
  IconCopy,
  IconLanguage,
  IconPlayerStop,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import { GlassCard } from '@/components/ui/GlassCard';
import { LANGUAGES } from '@/types/letter';
import type { StreamStatus } from '@/types/letter';

interface LetterOutputProps {
  status: StreamStatus;
  content: string;
  error: string | null;
  onStop: () => void;
  translatedContent: string;
  translateStatus: StreamStatus;
  translateError: string | null;
  onTranslate: (targetLanguage: string) => void;
  onResetTranslate: () => void;
}

type Tab = 'original' | 'translated';

const blinkKf = keyframes`
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
`;

const shimmerKf = keyframes`
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
`;

function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

function IdleState() {
  return (
    <Flex
      direction="column"
      align="center"
      justify="center"
      minH="640px"
      gap={6}
      px={6}
    >
      <Box position="relative" w="220px" h="220px">
        <Box
          position="absolute"
          inset={0}
          borderRadius="full"
          sx={{
            background:
              'radial-gradient(circle at 30% 30%, rgba(99,102,241,0.5) 0%, rgba(217,70,239,0.3) 45%, rgba(6,182,212,0.25) 75%, transparent 100%)',
            filter: 'blur(36px)',
          }}
        />
        <Box
          position="absolute"
          inset="20%"
          borderRadius="full"
          sx={{
            background:
              'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.7) 0%, transparent 70%)',
            filter: 'blur(20px)',
          }}
        />
      </Box>
      <Box textAlign="center" maxW="320px">
        <Text fontFamily="heading" fontSize="lg" fontWeight={600} color="slate.900" mb={1}>
          Готовы создать письмо
        </Text>
        <Text fontSize="sm" color="slate.500">
          Заполните форму слева — результат появится здесь
        </Text>
      </Box>
    </Flex>
  );
}

function ParsingState() {
  return (
    <Box minH="640px" p={10}>
      <Text fontSize="sm" color="slate.500" mb={6} fontFamily="mono">
        analysing job post…
      </Text>
      {Array.from({ length: 8 }).map((_, i) => (
        <Box
          key={i}
          position="relative"
          overflow="hidden"
          h="14px"
          mb={4}
          borderRadius="full"
          bg="rgba(99,102,241,0.08)"
          w={`${75 + ((i * 7) % 22)}%`}
        >
          <Box
            position="absolute"
            inset={0}
            sx={{
              background:
                'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.6) 50%, transparent 100%)',
              animation: `${shimmerKf} 1.6s linear infinite`,
              animationDelay: `${i * 0.12}s`,
            }}
          />
        </Box>
      ))}
    </Box>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <Flex
      direction="column"
      align="center"
      justify="center"
      minH="640px"
      px={10}
      textAlign="center"
      gap={3}
    >
      <Text fontFamily="heading" fontSize="lg" fontWeight={600} color="danger.500">
        Не получилось
      </Text>
      <Text fontSize="sm" color="slate.500" maxW="360px">
        {message}
      </Text>
    </Flex>
  );
}

function FloatingToolbar({
  isStreaming,
  isDone,
  onStop,
  onCopy,
  copied,
  onTranslate,
  wordCount,
  readMinutes,
}: {
  isStreaming: boolean;
  isDone: boolean;
  onStop: () => void;
  onCopy: () => void;
  copied: boolean;
  onTranslate: (targetLanguage: string) => void;
  wordCount: number;
  readMinutes: number;
}) {
  return (
    <Flex
      align="center"
      gap={2}
      px={3}
      py={2}
      borderRadius="full"
      bg="rgba(255,255,255,0.7)"
      border="1px solid rgba(255,255,255,0.7)"
      boxShadow="0 6px 24px rgba(15,23,42,0.08)"
      sx={{
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
      }}
    >
      <Flex
        align="center"
        gap={1.5}
        px={3}
        py={1}
        borderRadius="full"
        bg="rgba(99,102,241,0.08)"
        fontFamily="mono"
        fontSize="xs"
        color="slate.700"
      >
        <Text fontWeight={600}>{wordCount}</Text>
        <Text color="slate.500">words</Text>
        <Text color="slate.300">•</Text>
        <Text fontWeight={600}>{readMinutes}</Text>
        <Text color="slate.500">min</Text>
      </Flex>

      <Box flex="1" />

      <Menu placement="bottom-end">
        <Tooltip label="Перевести" hasArrow placement="top">
          <MenuButton
            as={IconButton}
            aria-label="Translate"
            icon={<IconLanguage size={18} stroke={1.75} />}
            size="sm"
            variant="ghost"
            color="slate.600"
            isDisabled={!isDone}
            _hover={{ color: 'aurora.indigo', bg: 'surface.glassStrong' }}
          />
        </Tooltip>
        <MenuList maxH="320px" overflowY="auto">
          {LANGUAGES.map((lang) => (
            <MenuItem
              key={lang.code}
              onClick={() => onTranslate(lang.apiName)}
              fontSize="sm"
            >
              {lang.label}
            </MenuItem>
          ))}
        </MenuList>
      </Menu>

      <Tooltip label={copied ? 'Скопировано' : 'Копировать'} hasArrow placement="top">
        <IconButton
          aria-label="Copy"
          icon={
            copied ? (
              <IconCheck size={18} stroke={2} color="#10B981" />
            ) : (
              <IconCopy size={18} stroke={1.75} />
            )
          }
          size="sm"
          variant="ghost"
          color="slate.600"
          onClick={onCopy}
          _hover={{ color: 'aurora.indigo', bg: 'surface.glassStrong' }}
        />
      </Tooltip>

      {isStreaming && (
        <Tooltip label="Остановить" hasArrow placement="top">
          <IconButton
            aria-label="Stop"
            icon={<IconPlayerStop size={18} stroke={1.75} />}
            size="sm"
            variant="ghost"
            color="danger.500"
            onClick={onStop}
            _hover={{ bg: 'rgba(225,29,72,0.08)' }}
          />
        </Tooltip>
      )}
    </Flex>
  );
}

function TabSwitch({
  tab,
  onChange,
  hasTranslation,
}: {
  tab: Tab;
  onChange: (t: Tab) => void;
  hasTranslation: boolean;
}) {
  if (!hasTranslation) return null;
  const tabs: { value: Tab; label: string }[] = [
    { value: 'original', label: 'Оригинал' },
    { value: 'translated', label: 'Перевод' },
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
      {tabs.map((t) => {
        const active = t.value === tab;
        return (
          <Box
            key={t.value}
            as="button"
            type="button"
            onClick={() => onChange(t.value)}
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
                layoutId="letter-output-tab-indicator"
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
            {t.label}
          </Box>
        );
      })}
    </Flex>
  );
}

function StreamingText({ text, isStreaming }: { text: string; isStreaming: boolean }) {
  return (
    <Box
      whiteSpace="pre-wrap"
      fontFamily="body"
      fontSize="md"
      lineHeight={1.75}
      color="slate.900"
      maxW="70ch"
    >
      <motion.span layout style={{ display: 'inline' }}>
        {text}
      </motion.span>
      {isStreaming && (
        <Box
          as="span"
          display="inline-block"
          w="2px"
          h="1.1em"
          ml="2px"
          verticalAlign="text-bottom"
          bg="aurora.indigo"
          sx={{ animation: `${blinkKf} 1s steps(1) infinite` }}
        />
      )}
    </Box>
  );
}

export function LetterOutput({
  status,
  content,
  error,
  onStop,
  translatedContent,
  translateStatus,
  translateError,
  onTranslate,
  onResetTranslate: _onResetTranslate,
}: LetterOutputProps) {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>('original');
  const [copied, setCopied] = useState(false);

  const isStreaming = status === 'parsing' || status === 'streaming';
  const isDone = status === 'done';
  const hasContent = !!content && (status === 'streaming' || status === 'done');
  const hasTranslation =
    (translateStatus === 'streaming' || translateStatus === 'done') && !!translatedContent;
  const showTranslated = tab === 'translated' && hasTranslation;
  const displayText = showTranslated ? translatedContent : content;
  const showStreamingCaret = showTranslated
    ? translateStatus === 'streaming'
    : status === 'streaming';

  const wordCount = useMemo(() => countWords(displayText), [displayText]);
  const readMinutes = Math.max(1, Math.ceil(wordCount / 200));

  const handleCopy = async () => {
    if (!displayText) return;
    try {
      await navigator.clipboard.writeText(displayText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast({
        title: 'Не удалось скопировать',
        status: 'error',
        duration: 2500,
        isClosable: true,
      });
    }
  };

  const handleTranslate = (target: string) => {
    setTab('translated');
    onTranslate(target);
  };

  // Auto-switch to translated tab when translation starts arriving.
  if (translateStatus === 'streaming' && tab !== 'translated') {
    setTab('translated');
  }

  // Idle / parsing / error / streamed states
  if (status === 'idle') {
    return (
      <GlassCard padding={0}>
        <IdleState />
      </GlassCard>
    );
  }

  if (status === 'parsing' && !content) {
    return (
      <GlassCard padding={0}>
        <ParsingState />
      </GlassCard>
    );
  }

  if (status === 'error' && error) {
    return (
      <GlassCard padding={0}>
        <ErrorState message={error} />
      </GlassCard>
    );
  }

  return (
    <GlassCard padding={0} position="relative">
      <Flex
        position="absolute"
        top="-18px"
        right={6}
        left={6}
        justify="space-between"
        align="center"
        zIndex={2}
        gap={4}
      >
        <TabSwitch tab={tab} onChange={setTab} hasTranslation={hasTranslation} />
        <FloatingToolbar
          isStreaming={isStreaming || translateStatus === 'streaming'}
          isDone={isDone}
          onStop={onStop}
          onCopy={handleCopy}
          copied={copied}
          onTranslate={handleTranslate}
          wordCount={wordCount}
          readMinutes={readMinutes}
        />
      </Flex>

      <Box
        mt={8}
        mx={6}
        mb={6}
        minH="640px"
        p={10}
        borderRadius="2xl"
        bg="rgba(255,255,255,0.6)"
        border="1px solid"
        borderColor="rgba(255,255,255,0.7)"
      >
        {hasContent ? (
          <StreamingText text={displayText} isStreaming={showStreamingCaret} />
        ) : (
          <Text color="slate.500" fontSize="sm">
            Загружаем...
          </Text>
        )}
      </Box>

      {translateError && (
        <Box mx={6} mb={6}>
          <Text fontSize="sm" color="danger.500">
            {translateError}
          </Text>
        </Box>
      )}
    </GlassCard>
  );
}

export default LetterOutput;
