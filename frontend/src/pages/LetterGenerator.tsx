import { useState } from 'react';
import { Box, Grid, Heading, Text } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useStreamLetter, useStreamTranslate } from '@/hooks/useLetter';
import LetterForm, { type LetterFormMode } from '@/components/letter/LetterForm';
import LetterOutput from '@/components/letter/LetterOutput';
import { TodayStatsCard } from '@/components/ui/TodayStatsCard';

export default function LetterGenerator() {
  const { t } = useTranslation();
  const [mode, setMode] = useState<LetterFormMode>('url');
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [generateLanguage, setGenerateLanguage] = useState<string>('');

  const {
    content: streamContent,
    status: streamStatus,
    error: streamError,
    generationTimeMs,
    streamFromUrl,
    streamFromText,
    reset: resetStream,
  } = useStreamLetter();
  const {
    content: translatedContent,
    status: translateStatus,
    error: translateError,
    translate,
    reset: resetTranslate,
  } = useStreamTranslate();

  const isBusy = streamStatus === 'parsing' || streamStatus === 'streaming';

  const handleSubmit = () => {
    resetTranslate();
    if (mode === 'url') {
      streamFromUrl({ url });
    } else {
      streamFromText({ name, description });
    }
  };

  const handleTranslate = (targetLanguage: string) => {
    if (!streamContent) return;
    resetTranslate();
    translate({ text: streamContent, target_language: targetLanguage });
  };

  return (
    <Box>
      <TodayStatsCard />

      <Box mb={8}>
        <Heading
          fontFamily="heading"
          fontSize="3xl"
          fontWeight={600}
          color="slate.900"
          letterSpacing="-0.02em"
          mb={1}
        >
          {t('letterGenerator.title')}
        </Heading>
        <Text color="slate.500" fontSize="sm">
          {t('letterGenerator.subtitle')}
        </Text>
      </Box>

      <Grid
        templateColumns={{ base: '1fr', lg: '1fr 1.5fr' }}
        gap={{ base: 6, lg: 8 }}
        alignItems="start"
      >
        <LetterForm
          mode={mode}
          onModeChange={setMode}
          url={url}
          onUrlChange={setUrl}
          name={name}
          onNameChange={setName}
          description={description}
          onDescriptionChange={setDescription}
          language={generateLanguage}
          onLanguageChange={setGenerateLanguage}
          isBusy={isBusy}
          onSubmit={handleSubmit}
        />

        <LetterOutput
          status={streamStatus}
          content={streamContent}
          error={streamError}
          onStop={resetStream}
          translatedContent={translatedContent}
          translateStatus={translateStatus}
          translateError={translateError}
          onTranslate={handleTranslate}
          onResetTranslate={resetTranslate}
          jobUrl={mode === 'url' ? url : undefined}
          jobName={mode === 'text' ? name : undefined}
          generationTimeMs={generationTimeMs}
          onSaved={() => {
            setUrl('');
            setName('');
            setDescription('');
          }}
          onSwitchToText={() => setMode('text')}
        />
      </Grid>
    </Box>
  );
}
