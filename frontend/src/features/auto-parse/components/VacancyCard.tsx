import { useState } from 'react';
import {
  Box,
  Button,
  Flex,
  Link,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { IconCheck, IconEye, IconExternalLink, IconMapPin, IconSparkles } from '@tabler/icons-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { VacancyModal } from './VacancyModal';
import { autoParseApi } from '../api/auto-parse-client';
import type { AutoParsedJob, GenerationMode } from '../types';
import { useTranslation } from 'react-i18next';

function copyLetterOnVacancyOpen(letter: string | null): void {
  if (letter?.trim()) {
    void navigator.clipboard?.writeText(letter);
  }
}

interface VacancyCardProps {
  vacancy: AutoParsedJob;
  variant?: 'compact' | 'hh';
  generationMode?: GenerationMode;
  isTemplateGenerationPending?: boolean;
}

function CompactVacancyCard({ vacancy, generationMode = 'ai', isTemplateGenerationPending = false }: VacancyCardProps) {
  const { t } = useTranslation();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [autoGenerate, setAutoGenerate] = useState(false);
  const [isApplied, setIsApplied] = useState(vacancy.is_applied);
  const [isViewed, setIsViewed] = useState(vacancy.is_viewed);
  // is_generated is updated by the parent via SSE so we read it from the prop
  const isGenerated = vacancy.is_generated;

  const openCard = () => {
    onOpen();
    if (!isViewed) {
      setIsViewed(true);
      autoParseApi.markViewed(vacancy.id).catch(() => setIsViewed(false));
    }
  };

  const handleCardClick = () => {
    setAutoGenerate(false);
    openCard();
  };

  const handleGenerate = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isTemplateGenerationPending) return;
    setAutoGenerate(true);
    openCard();
  };
  const openVacancy = (event: React.MouseEvent) => {
    event.stopPropagation();
    copyLetterOnVacancyOpen(vacancy.cover_letter_text);
    if (!isViewed) {
      setIsViewed(true);
      autoParseApi.markViewed(vacancy.id).catch(() => setIsViewed(false));
    }
  };

  return (
    <>
      <Box
        onClick={handleCardClick}
        cursor="pointer"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleCardClick()}
      >
        <GlassCard hover padding={5} opacity={isApplied ? 0.62 : 1}>
          <Flex direction="column" gap={3} h="100%">
            {/* Title row */}
            <Flex direction={"column"} gap="10px">
              <Text
                fontFamily="heading"
                fontSize="md"
                fontWeight={600}
                color="slate.900"
                letterSpacing="-0.01em"
                noOfLines={2}
              >
                {vacancy.job_title}
              </Text>

              {vacancy.web_site && URL.canParse(vacancy.web_site) && (
                <Link
                  href={vacancy.web_site}
                  isExternal
                  display="inline-flex"
                  alignItems="center"
                  gap={1.5}
                  fontSize="sm"
                  fontWeight={600}
                  color="aurora.indigo"
                  _hover={{ textDecoration: 'underline' }}
                >
                  {t('autoParse.employerLink')}
                  <IconExternalLink size={14} stroke={2} />
                </Link>
                // <Text as={"a"} fontSize={"sm"} href={vacancy.web_site}>{t('autoParse.employerLink')}</Text>
              )}
              {isApplied && (
                <Flex align="center" gap={1} w="fit-content" bg="green.100" border="1px solid" borderColor="green.300" borderRadius="lg" px={2} py={1}>
                  <IconCheck size={12} stroke={2.5} color="var(--chakra-colors-green-700)" />
                  <Text fontSize="xs" fontWeight={700} color="green.700">Уже откликались</Text>
                </Flex>
              )}
            </Flex>


            {/* Truncated description */}
            <Text fontSize="sm" color="slate.600" lineHeight={1.65} noOfLines={3} flex="1">
              {vacancy.job_text}
            </Text>

            {/* External link */}
            <Box>
              <Link
                href={vacancy.url}
                isExternal
                display="inline-flex"
                alignItems="center"
                gap={1}
                fontSize="xs"
                fontWeight={600}
                color="aurora.indigo"
                _hover={{ textDecoration: 'underline' }}
                onClick={openVacancy}
              >
                Открыть страницу вакансии
                <Box as="span" display="inline-flex" alignItems="center">
                  <IconExternalLink size={12} stroke={2} />
                </Box>
              </Link>
            </Box>

            {/* Status badges */}
            {(isGenerated || isApplied || isViewed) && (
              <Flex gap={1} flexWrap="wrap">
                {isGenerated && (
                  <Flex
                    align="center"
                    gap={1}
                    bg="purple.50"
                    border="1px solid"
                    borderColor="purple.200"
                    borderRadius="lg"
                    px={2}
                    py={0.5}
                  >
                    <IconSparkles size={11} stroke={2.5} color="var(--chakra-colors-purple-600)" />
                    <Text fontSize="xs" fontWeight={600} color="purple.600" whiteSpace="nowrap">
                      Письмо готово
                    </Text>
                  </Flex>
                )}
                {isApplied && (
                  <Flex
                    align="center"
                    gap={1}
                    bg="green.50"
                    border="1px solid"
                    borderColor="green.200"
                    borderRadius="lg"
                    px={2}
                    py={0.5}
                  >
                    <IconCheck size={11} stroke={2.5} color="var(--chakra-colors-green-600)" />
                    <Text fontSize="xs" fontWeight={600} color="green.600" whiteSpace="nowrap">
                      Откликнулись
                    </Text>
                  </Flex>
                )}
                {isViewed && (
                  <Flex
                    align="center"
                    gap={1}
                    bg="gray.50"
                    border="1px solid"
                    borderColor="gray.200"
                    borderRadius="lg"
                    px={2}
                    py={0.5}
                  >
                    <IconEye size={11} stroke={2.5} color="var(--chakra-colors-gray-500)" />
                    <Text fontSize="xs" fontWeight={600} color="gray.500" whiteSpace="nowrap">
                      Просмотрено
                    </Text>
                  </Flex>
                )}
              </Flex>
            )}

            {/* Generate button */}
            <Box pt={1}>
              <GradientButton
                size="sm"
                onClick={handleGenerate}
                leftIcon={<IconSparkles size={13} stroke={2} />}
                w="full"
                height={8}
                fontSize="xs"
                isDisabled={isTemplateGenerationPending}
              >
                {isGenerated ? 'Посмотреть письмо' : isTemplateGenerationPending ? 'Письмо готовится автоматически' : 'Сгенерировать'}
              </GradientButton>
            </Box>
          </Flex>
        </GlassCard>
      </Box>

      <VacancyModal
        vacancy={vacancy}
        isOpen={isOpen}
        onClose={onClose}
        autoGenerate={autoGenerate && !isGenerated}
        generationMode={generationMode}
        isTemplateGenerationPending={isTemplateGenerationPending}
        onApplied={() => setIsApplied(true)}
      />
    </>
  );
}

function HHVacancyCard({ vacancy, generationMode = 'ai', isTemplateGenerationPending = false }: VacancyCardProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [autoGenerate, setAutoGenerate] = useState(false);
  const [isApplied, setIsApplied] = useState(vacancy.is_applied);
  const [isViewed, setIsViewed] = useState(vacancy.is_viewed);

  const openCard = () => {
    onOpen();
    if (!isViewed) {
      setIsViewed(true);
      autoParseApi.markViewed(vacancy.id).catch(() => setIsViewed(false));
    }
  };
  const generate = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (isTemplateGenerationPending) return;
    setAutoGenerate(true);
    openCard();
  };
  const openVacancy = (event: React.MouseEvent) => {
    event.stopPropagation();
    copyLetterOnVacancyOpen(vacancy.cover_letter_text);
    if (!isViewed) {
      setIsViewed(true);
      autoParseApi.markViewed(vacancy.id).catch(() => setIsViewed(false));
    }
  };
  const markApplied = async (event: React.MouseEvent) => {
    event.stopPropagation();
    if (isApplied) return;
    await autoParseApi.markApplied(vacancy.id, vacancy.cover_letter_text ?? undefined);
    setIsApplied(true);
  };

  return (
    <>
      <Box onClick={openCard} cursor="pointer" role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && openCard()}>
        <Box bg="white" opacity={isApplied ? 0.62 : 1} border="1px solid" borderColor="slate.200" borderRadius="2xl" overflow="hidden" position="relative" boxShadow="0 4px 18px rgba(15, 23, 42, 0.04)" _hover={{ borderColor: 'blue.300', boxShadow: '0 10px 28px rgba(37, 99, 235, 0.10)' }}>
          <Box position="absolute" left={0} top={5} h={10} w={1.5} bg="orange.300" borderRightRadius="full" />
          <Flex direction="column" gap={3.5} px={{ base: 5, md: 6 }} py={5} pl={{ base: 6, md: 7 }}>
            <Flex justify="space-between" align="flex-start" gap={4}>
              <Box minW={0}>
                <Text fontFamily="heading" fontSize={{ base: 'md', md: 'lg' }} fontWeight={700} color="slate.900" noOfLines={2}>{vacancy.job_title}</Text>
                {isApplied && <Flex mt={2} align="center" gap={1} w="fit-content" bg="green.100" border="1px solid" borderColor="green.300" borderRadius="lg" px={2} py={1}><IconCheck size={12} stroke={2.5} color="var(--chakra-colors-green-700)" /><Text fontSize="xs" fontWeight={700} color="green.700">Уже откликались</Text></Flex>}
                <Text mt={1.5} color="slate.600" fontSize="sm" lineHeight={1.55} noOfLines={2}>{vacancy.job_text}</Text>
              </Box>
              <Flex align="center" gap={3} flexShrink={0}>
                {isViewed && (
                  <Flex align="center" gap={1} color="slate.500" aria-label="Просмотрено">
                    <IconEye size={18} stroke={1.9} />
                    <Text fontSize="xs" fontWeight={600}>Просмотрено</Text>
                  </Flex>
                )}
                <Button size="sm" colorScheme={isApplied ? 'green' : 'blue'} variant={isApplied ? 'solid' : 'outline'} leftIcon={<IconCheck size={14} />} isDisabled={isApplied} onClick={markApplied}>
                  {isApplied ? 'Откликнулись' : 'Откликнуться?'}
                </Button>
              </Flex>
            </Flex>
            <Box>
              <Text fontSize="sm" fontWeight={650} color="slate.800">{vacancy.web_site || 'Вакансия от работодателя'}</Text>
              <Flex mt={1.5} align="center" gap={1.5} color="slate.600" fontSize="sm"><IconMapPin size={15} stroke={1.8} /><Text>Локация указана в вакансии</Text></Flex>
            </Box>
            <Flex justify="space-between" align={{ base: 'stretch', sm: 'center' }} direction={{ base: 'column', sm: 'row' }} gap={3}>
              <GradientButton size="md" px={6} onClick={generate} isDisabled={isTemplateGenerationPending} leftIcon={<IconSparkles size={16} stroke={2} />}>{vacancy.is_generated ? 'Посмотреть письмо' : isTemplateGenerationPending ? 'Письмо готовится автоматически' : 'Сгенерировать'}</GradientButton>
              <Link href={vacancy.url} isExternal onClick={openVacancy} color="blue.600" fontSize="sm" fontWeight={600}>Открыть вакансию <IconExternalLink size={14} style={{ display: 'inline', verticalAlign: 'middle' }} /></Link>
            </Flex>
          </Flex>
        </Box>
      </Box>
      <VacancyModal vacancy={vacancy} isOpen={isOpen} onClose={onClose} autoGenerate={autoGenerate && !vacancy.is_generated} generationMode={generationMode} isTemplateGenerationPending={isTemplateGenerationPending} onApplied={() => setIsApplied(true)} />
    </>
  );
}

export function VacancyCard({ vacancy, variant = 'compact', generationMode, isTemplateGenerationPending }: VacancyCardProps) {
  return variant === 'hh' ? <HHVacancyCard vacancy={vacancy} generationMode={generationMode} isTemplateGenerationPending={isTemplateGenerationPending} /> : <CompactVacancyCard vacancy={vacancy} generationMode={generationMode} isTemplateGenerationPending={isTemplateGenerationPending} />;
}
