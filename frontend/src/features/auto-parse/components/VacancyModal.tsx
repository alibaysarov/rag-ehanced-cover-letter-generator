import {
  Box,
  Button,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
} from '@chakra-ui/react';
import { IconExternalLink } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import type { AutoParsedJob } from '../types';

interface VacancyModalProps {
  vacancy: AutoParsedJob;
  isOpen: boolean;
  onClose: () => void;
}

export function VacancyModal({ vacancy, isOpen, onClose }: VacancyModalProps) {
  const { t } = useTranslation();

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
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
        <ModalHeader
          fontFamily="heading"
          fontWeight={600}
          fontSize="lg"
          color="slate.900"
          letterSpacing="-0.01em"
          pb={2}
        >
          {vacancy.job_title}
        </ModalHeader>
        <ModalCloseButton color="slate.500" top={4} right={4} />

        <ModalBody>
          <Text
            fontSize="sm"
            color="slate.700"
            whiteSpace="pre-wrap"
            lineHeight={1.7}
          >
            {vacancy.job_text}
          </Text>
        </ModalBody>

        <ModalFooter gap={3}>
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
              {t('autoParse.vacancyLink')}
              <IconExternalLink size={14} stroke={2} />
            </Link>
          </Box>
          <Button
            size="sm"
            borderRadius="xl"
            variant="ghost"
            color="slate.600"
            onClick={onClose}
            _hover={{ bg: 'rgba(99,102,241,0.08)', color: 'aurora.indigo' }}
          >
            {t('autoParse.close', 'Close')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
