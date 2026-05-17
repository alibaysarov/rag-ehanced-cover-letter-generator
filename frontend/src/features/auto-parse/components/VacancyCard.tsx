import { useState } from 'react';
import {
  Box,
  Flex,
  Link,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { IconCheck, IconExternalLink, IconSparkles } from '@tabler/icons-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { VacancyModal } from './VacancyModal';
import type { AutoParsedJob } from '../types';

interface VacancyCardProps {
  vacancy: AutoParsedJob;
}

export function VacancyCard({ vacancy }: VacancyCardProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [autoGenerate, setAutoGenerate] = useState(false);
  const [isApplied, setIsApplied] = useState(vacancy.is_applied);
  // is_generated is updated by the parent via SSE so we read it from the prop
  const isGenerated = vacancy.is_generated;

  const handleCardClick = () => {
    setAutoGenerate(false);
    onOpen();
  };

  const handleGenerate = (e: React.MouseEvent) => {
    e.stopPropagation();
    setAutoGenerate(true);
    onOpen();
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
            <Flex align="flex-start" justify="space-between" gap={2}>
              <Text
                fontFamily="heading"
                fontSize="md"
                fontWeight={600}
                color="slate.900"
                letterSpacing="-0.01em"
                noOfLines={2}
                flex="1"
              >
                {vacancy.job_title}
              </Text>
              <Flex gap={1} flexShrink={0} flexWrap="wrap" justify="flex-end">
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
              </Flex>
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
                Открыть на hh.ru
                <Box as="span" display="inline-flex" alignItems="center">
                  <IconExternalLink size={12} stroke={2} />
                </Box>
              </Link>
            </Box>

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
