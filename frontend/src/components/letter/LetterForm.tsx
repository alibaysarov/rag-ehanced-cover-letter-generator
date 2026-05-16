import { useEffect } from 'react';
import {
  Box,
  Flex,
  FormControl,
  FormLabel,
  Input,
  Select,
  Stack,
  Text,
  Textarea,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { LANGUAGES } from '@/types/letter';

const DEFAULT_GEN_LANG_KEY = 'aurora.defaultGenLang';

export type LetterFormMode = 'url' | 'text';

interface LetterFormProps {
  mode: LetterFormMode;
  onModeChange: (mode: LetterFormMode) => void;
  url: string;
  onUrlChange: (v: string) => void;
  name: string;
  onNameChange: (v: string) => void;
  description: string;
  onDescriptionChange: (v: string) => void;
  language: string;
  onLanguageChange: (v: string) => void;
  isBusy: boolean;
  onSubmit: () => void;
}

function ModeToggle({
  mode,
  onModeChange,
}: {
  mode: LetterFormMode;
  onModeChange: (m: LetterFormMode) => void;
}) {
  const options: { value: LetterFormMode; label: string }[] = [
    { value: 'url', label: 'From URL' },
    { value: 'text', label: 'From Text' },
  ];

  return (
    <Flex
      position="relative"
      bg="rgba(255,255,255,0.5)"
      borderRadius="full"
      p={1}
      border="1px solid"
      borderColor="slate.200"
      gap={1}
      w="fit-content"
    >
      {options.map((o) => {
        const active = o.value === mode;
        return (
          <Box
            key={o.value}
            as="button"
            type="button"
            onClick={() => onModeChange(o.value)}
            position="relative"
            px={6}
            py={2}
            borderRadius="full"
            fontSize="sm"
            fontWeight={600}
            color={active ? 'white' : 'slate.700'}
            transition="color 200ms ease"
            _hover={!active ? { color: 'slate.900' } : undefined}
            zIndex={1}
          >
            {active && (
              <motion.div
                layoutId="letter-form-mode-indicator"
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

export function LetterForm({
  mode,
  onModeChange,
  url,
  onUrlChange,
  name,
  onNameChange,
  description,
  onDescriptionChange,
  language,
  onLanguageChange,
  isBusy,
  onSubmit,
}: LetterFormProps) {
  // Preference: pick up the user's default generation language on first mount
  // unless they already chose one in this session.
  useEffect(() => {
    if (language) return;
    const stored = localStorage.getItem(DEFAULT_GEN_LANG_KEY);
    if (stored) {
      const match = LANGUAGES.find((l) => l.code === stored);
      if (match) onLanguageChange(match.apiName);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  const canSubmit =
    !isBusy && (mode === 'url' ? !!url.trim() : !!name.trim() && !!description.trim());

  return (
    <GlassCard padding={{ base: 6, md: 8 }}>
      <Stack spacing={6}>
        <Box>
          <Text
            fontFamily="heading"
            fontSize="lg"
            fontWeight={600}
            color="slate.900"
            letterSpacing="-0.01em"
            mb={3}
          >
            Создать письмо
          </Text>
          <ModeToggle mode={mode} onModeChange={onModeChange} />
        </Box>

        <form onSubmit={handleSubmit}>
          <Stack spacing={5}>
            {mode === 'url' ? (
              <FormControl isRequired>
                <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                  URL вакансии
                </FormLabel>
                <Input
                  type="url"
                  placeholder="https://example.com/job-description"
                  value={url}
                  onChange={(e) => onUrlChange(e.target.value)}
                  fontFamily="mono"
                  fontSize="sm"
                />
              </FormControl>
            ) : (
              <>
                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                    Название позиции
                  </FormLabel>
                  <Input
                    placeholder="Senior Frontend Engineer"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                  />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                    Описание вакансии
                  </FormLabel>
                  <Textarea
                    placeholder="Опишите требования и обязанности..."
                    value={description}
                    onChange={(e) => onDescriptionChange(e.target.value)}
                    rows={10}
                    resize="vertical"
                  />
                </FormControl>
              </>
            )}

            <FormControl>
              <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                Язык письма
              </FormLabel>
              <Select
                placeholder="Авто (по тексту вакансии)"
                value={language}
                onChange={(e) => onLanguageChange(e.target.value)}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.apiName}>
                    {lang.label}
                  </option>
                ))}
              </Select>
            </FormControl>

            <GradientButton
              type="submit"
              size="lg"
              w="full"
              isLoading={isBusy}
              loadingText="Генерируем..."
              isDisabled={!canSubmit}
              mt={2}
            >
              Сгенерировать
            </GradientButton>
          </Stack>
        </form>
      </Stack>
    </GlassCard>
  );
}

export default LetterForm;
