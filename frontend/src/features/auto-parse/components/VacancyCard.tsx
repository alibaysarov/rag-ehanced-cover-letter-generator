import { useState } from 'react';
import {
  Box,
  Flex,
  Link,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { IconCheck, IconEye, IconExternalLink, IconHeart, IconMapPin, IconMessageCircle, IconSparkles } from '@tabler/icons-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { VacancyModal } from './VacancyModal';
import { autoParseApi } from '../api/auto-parse-client';
import type { AutoParsedJob } from '../types';
import { useTranslation } from 'react-i18next';

interface VacancyCardProps {
  vacancy: AutoParsedJob;
  variant?: 'compact' | 'hh';
}

function CompactVacancyCard({ vacancy }: VacancyCardProps) {
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
    setAutoGenerate(true);
    openCard();
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
        <GlassCard hover padding={5}>
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
                onClick={(e) => e.stopPropagation()}
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
              >
                {isGenerated ? 'Посмотреть письмо' : 'Сгенерировать'}
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
        onApplied={() => setIsApplied(true)}
      />
    </>
  );
}

function HHVacancyCard({ vacancy }: VacancyCardProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [autoGenerate, setAutoGenerate] = useState(false);
  const [, setIsApplied] = useState(vacancy.is_applied);
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
    setAutoGenerate(true);
    openCard();
  };

  return (
    <>
      <Box onClick={openCard} cursor="pointer" role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && openCard()}>
        <Box bg="white" border="1px solid" borderColor="slate.200" borderRadius="2xl" overflow="hidden" position="relative" boxShadow="0 4px 18px rgba(15, 23, 42, 0.04)" _hover={{ borderColor: 'blue.300', boxShadow: '0 10px 28px rgba(37, 99, 235, 0.10)' }}>
          <Box position="absolute" left={0} top={5} h={10} w={1.5} bg="orange.300" borderRightRadius="full" />
          <Flex direction="column" gap={3.5} px={{ base: 5, md: 6 }} py={5} pl={{ base: 6, md: 7 }}>
            <Flex justify="space-between" align="flex-start" gap={4}>
              <Box minW={0}>
                <Text fontFamily="heading" fontSize={{ base: 'md', md: 'lg' }} fontWeight={700} color="slate.900" noOfLines={2}>{vacancy.job_title}</Text>
                <Text mt={1.5} color="slate.600" fontSize="sm" lineHeight={1.55} noOfLines={2}>{vacancy.job_text}</Text>
              </Box>
              <Flex color="slate.400" gap={3} flexShrink={0}><IconMessageCircle size={22} stroke={1.8} /><IconHeart size={22} stroke={1.8} /></Flex>
            </Flex>
            <Box>
              <Text fontSize="sm" fontWeight={650} color="slate.800">{vacancy.web_site || 'Вакансия от работодателя'}</Text>
              <Flex mt={1.5} align="center" gap={1.5} color="slate.600" fontSize="sm"><IconMapPin size={15} stroke={1.8} /><Text>Локация указана в вакансии</Text></Flex>
            </Box>
            <Flex justify="space-between" align={{ base: 'stretch', sm: 'center' }} direction={{ base: 'column', sm: 'row' }} gap={3}>
              <GradientButton size="md" px={6} onClick={generate} leftIcon={<IconSparkles size={16} stroke={2} />}>{vacancy.is_generated ? 'Посмотреть письмо' : 'Сгенерировать'}</GradientButton>
              <Link href={vacancy.url} isExternal onClick={(event) => event.stopPropagation()} color="blue.600" fontSize="sm" fontWeight={600}>Открыть вакансию <IconExternalLink size={14} style={{ display: 'inline', verticalAlign: 'middle' }} /></Link>
            </Flex>
          </Flex>
        </Box>
      </Box>
      <VacancyModal vacancy={vacancy} isOpen={isOpen} onClose={onClose} autoGenerate={autoGenerate && !vacancy.is_generated} onApplied={() => setIsApplied(true)} />
    </>
  );
}

export function VacancyCard({ vacancy, variant = 'compact' }: VacancyCardProps) {
  return variant === 'hh' ? <HHVacancyCard vacancy={vacancy} /> : <CompactVacancyCard vacancy={vacancy} />;
}
