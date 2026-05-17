import {
  Box,
  Flex,
  Link,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { IconExternalLink, IconEye } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { VacancyModal } from './VacancyModal';
import type { AutoParsedJob } from '../types';

interface VacancyCardProps {
  vacancy: AutoParsedJob;
}

export function VacancyCard({ vacancy }: VacancyCardProps) {
  const { t } = useTranslation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <>
      <GlassCard hover padding={5}>
        <Flex direction="column" gap={3} h="100%">
          {/* Title */}
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

          {/* Truncated description */}
          <Text
            fontSize="sm"
            color="slate.600"
            lineHeight={1.65}
            noOfLines={3}
            flex="1"
          >
            {vacancy.job_text}
          </Text>

          {/* Actions */}
          <Flex align="center" justify="space-between" pt={1} flexWrap="wrap" gap={2}>
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
            >
              {t('autoParse.vacancyLink')}
              <Box as="span" display="inline-flex" alignItems="center">
                <IconExternalLink size={12} stroke={2} />
              </Box>
            </Link>

            <GradientButton
              size="sm"
              onClick={onOpen}
              leftIcon={<IconEye size={14} stroke={2} />}
              px={4}
              height={8}
            >
              {t('autoParse.open')}
            </GradientButton>
          </Flex>
        </Flex>
      </GlassCard>

      <VacancyModal vacancy={vacancy} isOpen={isOpen} onClose={onClose} />
    </>
  );
}
