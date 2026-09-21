import {
  Alert,
  AlertIcon,
  Badge,
  Button,
  FormControl,
  FormErrorMessage,
  FormLabel,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Switch,
  Text,
  Textarea,
  useToast,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import axios from 'axios';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { letterConstructorApi } from '../api';
import type { LetterPhrase, PhraseType } from '../types';

const phraseTypes: PhraseType[] = [
  'opening',
  'experience_bridge',
  'portfolio_intro',
  'stack_summary',
  'closing',
  'custom',
];
const tokens = ['[[job_title]]', '[[company_name]]', '[[matched_technologies]]'];

interface Props {
  isOpen: boolean;
  phrase?: LetterPhrase;
  onClose: () => void;
  onSaved: (phrase: LetterPhrase) => void | Promise<void>;
}

export function PhraseFormModal({ isOpen, phrase, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [type, setType] = useState<PhraseType>('custom');
  const [text, setText] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setType(phrase?.type ?? 'custom');
    setText(phrase?.text ?? '');
    setIsActive(phrase?.is_active ?? true);
    setSubmitted(false);
  }, [isOpen, phrase]);

  const clean = text.trim();
  const textError = submitted && !clean
    ? t('letterConstructor.phraseForm.textRequired')
    : submitted && clean.length > 2000
      ? t('letterConstructor.phraseForm.textTooLong')
      : '';

  const insertToken = (token: string) => {
    const element = textarea.current;
    const start = element?.selectionStart ?? text.length;
    const end = element?.selectionEnd ?? start;
    const next = `${text.slice(0, start)}${token}${text.slice(end)}`;
    setText(next);
    requestAnimationFrame(() => {
      element?.focus();
      element?.setSelectionRange(start + token.length, start + token.length);
    });
  };

  const save = async () => {
    setSubmitted(true);
    if (!clean || clean.length > 2000) return;
    setSaving(true);
    try {
      const saved = phrase
        ? await letterConstructorApi.updatePhrase(phrase.id, {
            type,
            text: clean,
            is_active: isActive,
          })
        : await letterConstructorApi.createPhrase({
            type,
            text: clean,
            is_active: isActive,
          });
      await onSaved(saved);
      onClose();
    } catch (error) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast({
        status: 'error',
        title: t('letterConstructor.phraseForm.saveError'),
        description: typeof detail?.code === 'string' ? detail.code : undefined,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={saving ? () => undefined : onClose} size="xl" isCentered>
      <ModalOverlay bg="blackAlpha.500" backdropFilter="blur(4px)" />
      <ModalContent borderRadius="2xl">
        <ModalHeader>
          {t(phrase ? 'letterConstructor.phraseForm.editTitle' : 'letterConstructor.phraseForm.createTitle')}
        </ModalHeader>
        <ModalCloseButton isDisabled={saving} />
        <ModalBody>
          {phrase && phrase.used_in_templates > 0 && (
            <Alert status="warning" borderRadius="lg" mb={5}>
              <AlertIcon />
              {t('letterConstructor.phraseForm.impact', { count: phrase.used_in_templates })}
            </Alert>
          )}
          <FormControl isRequired mb={5}>
            <FormLabel>{t('letterConstructor.phraseForm.type')}</FormLabel>
            <Select value={type} onChange={(event) => setType(event.target.value as PhraseType)}>
              {phraseTypes.map((item) => (
                <option key={item} value={item}>
                  {t(`letterConstructor.phraseTypes.${item}`)}
                </option>
              ))}
            </Select>
          </FormControl>
          <FormControl isRequired isInvalid={Boolean(textError)}>
            <FormLabel>{t('letterConstructor.phraseForm.text')}</FormLabel>
            <Textarea
              ref={textarea}
              value={text}
              onChange={(event) => setText(event.target.value)}
              minH="180px"
              resize="vertical"
              placeholder={t('letterConstructor.phraseForm.placeholder')}
            />
            <HStack justify="space-between" mt={2} align="start">
              <FormErrorMessage mt={0}>{textError}</FormErrorMessage>
              <Text ml="auto" fontSize="xs" color={text.length > 2000 ? 'red.500' : 'gray.500'}>
                {text.length}/2000
              </Text>
            </HStack>
          </FormControl>
          <Text fontSize="sm" fontWeight="semibold" mt={5} mb={2}>
            {t('letterConstructor.phraseForm.tokens')}
          </Text>
          <Wrap spacing={2}>
            {tokens.map((token) => (
              <WrapItem key={token}>
                <Badge
                  as="button"
                  type="button"
                  colorScheme="purple"
                  px={3}
                  py={1.5}
                  borderRadius="full"
                  cursor="pointer"
                  onClick={() => insertToken(token)}
                >
                  {token}
                </Badge>
              </WrapItem>
            ))}
          </Wrap>
          <Text fontSize="xs" color="gray.500" mt={2}>
            {t('letterConstructor.phraseForm.tokensHint')}
          </Text>
          <FormControl mt={6} display="flex" alignItems="center">
            <Switch
              id="phrase-active"
              isChecked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              mr={3}
            />
            <FormLabel htmlFor="phrase-active" mb={0}>
              {t('letterConstructor.phraseForm.active')}
            </FormLabel>
          </FormControl>
        </ModalBody>
        <ModalFooter gap={3}>
          <Button variant="ghost" onClick={onClose} isDisabled={saving}>
            {t('letterConstructor.phraseForm.cancel')}
          </Button>
          <Button colorScheme="purple" onClick={save} isLoading={saving}>
            {t('letterConstructor.phraseForm.save')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
