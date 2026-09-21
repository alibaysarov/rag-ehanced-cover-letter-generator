import { useState, type FormEvent } from 'react';
import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  Code,
  FormControl,
  FormHelperText,
  FormLabel,
  Heading,
  HStack,
  Input,
  NumberInput,
  NumberInputField,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from '@chakra-ui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import type { ParserInput } from './types';

function FieldLabelWithTooltip({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <FormLabel display="flex" alignItems="center" justifyContent="space-between" gap={3}>
      <Text as="span">{label}</Text>
      <Tooltip label={tooltip} hasArrow placement="top" maxW="340px" px={3} py={2} borderRadius="lg">
        <Box
          as="span"
          display="inline-flex"
          color="aurora.indigo"
          cursor="help"
          tabIndex={0}
          aria-label={tooltip}
        >
          <IconInfoCircle size={19} stroke={1.8} />
        </Box>
      </Tooltip>
    </FormLabel>
  );
}

interface Props {
  initial: ParserInput;
  isSubmitting: boolean;
  isInUse?: boolean;
  error?: string;
  onSubmit: (value: ParserInput) => void;
  onCancel: () => void;
}

export function ParserForm({ initial, isSubmitting, isInUse, error, onSubmit, onCancel }: Props) {
  const { t } = useTranslation();
  const [value, setValue] = useState<ParserInput>(initial);
  const [params, setParams] = useState(
    Object.entries(initial.format_url.query_params).map(([key, item]) => ({ key, value: item })),
  );
  const set = <K extends keyof ParserInput>(key: K, next: ParserInput[K]) =>
    setValue((current) => ({ ...current, [key]: next }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      ...value,
      format_url: {
        ...value.format_url,
        query_params: Object.fromEntries(params.filter((item) => item.key.trim()).map((item) => [item.key.trim(), item.value])),
      },
      evaluate_pagination: value.evaluate_pagination || null,
    });
  };

  return (
    <Box as="form" onSubmit={submit} maxW="900px">
      <Stack spacing={7}>
        {isInUse && <Alert status="info" borderRadius="xl"><AlertIcon />{t('searchSites.editInUse')}</Alert>}
        {error && <Alert status="error" borderRadius="xl"><AlertIcon />{error}</Alert>}
        <Box bg="white" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.main')}</Heading>
          <Stack spacing={4}>
            <FormControl isRequired><FormLabel>{t('searchSites.fields.name')}</FormLabel><Input value={value.name} onChange={(e) => set('name', e.target.value)} /></FormControl>
            <FormControl isRequired>
              <FieldLabelWithTooltip
                label={t('searchSites.fields.baseUrl')}
                tooltip={t('searchSites.hints.baseUrlTooltip')}
              />
              <Input value={value.base_url} onChange={(e) => set('base_url', e.target.value)} />
              <FormHelperText lineHeight="tall">
                {t('searchSites.hints.example')} <Code colorScheme="purple">https://hh.ru/search/vacancy</Code>
                <br />
                {t('searchSites.hints.baseUrlExample')}
              </FormHelperText>
            </FormControl>
            <FormControl isRequired>
              <FieldLabelWithTooltip
                label={t('searchSites.fields.singleUrl')}
                tooltip={t('searchSites.hints.singleUrlTooltip')}
              />
              <Input value={value.single_url} onChange={(e) => set('single_url', e.target.value)} />
              <FormHelperText lineHeight="tall">
                {t('searchSites.hints.example')} <Code colorScheme="purple">{'https://hh.ru/vacancy/{vacancy_id}'}</Code>
                <br />
                {t('searchSites.hints.singleUrlExample')}
              </FormHelperText>
            </FormControl>
          </Stack>
        </Box>
        <Box bg="white" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.search')}</Heading>
          <FormControl isRequired mb={4}><FormLabel>{t('searchSites.fields.urlTemplate')}</FormLabel><Input value={value.format_url.url_template} onChange={(e) => set('format_url', { ...value.format_url, url_template: e.target.value })} /><FormHelperText>{t('searchSites.hints.templates')}</FormHelperText></FormControl>
          <FormLabel>{t('searchSites.fields.queryParams')}</FormLabel>
          <Stack spacing={2}>{params.map((item, index) => <HStack key={index}><Input placeholder="key" value={item.key} onChange={(e) => setParams((old) => old.map((row, i) => i === index ? { ...row, key: e.target.value } : row))} /><Input placeholder="value" value={item.value} onChange={(e) => setParams((old) => old.map((row, i) => i === index ? { ...row, value: e.target.value } : row))} /><Button onClick={() => setParams((old) => old.filter((_, i) => i !== index))}>−</Button></HStack>)}</Stack>
          <Button mt={3} size="sm" onClick={() => setParams((old) => [...old, { key: '', value: '' }])}>{t('searchSites.addParam')}</Button>
        </Box>
        <Box bg="white" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.pagination')}</Heading>
          <Checkbox isChecked={value.has_pagination} onChange={(e) => set('has_pagination', e.target.checked)}>{t('searchSites.fields.hasPagination')}</Checkbox>
          {value.has_pagination && <Stack mt={4} spacing={4}><HStack><FormControl><FormLabel>{t('searchSites.fields.paginationStart')}</FormLabel><NumberInput min={0} value={value.pagination_start} onChange={(_, n) => set('pagination_start', Number.isNaN(n) ? 0 : n)}><NumberInputField /></NumberInput></FormControl><FormControl><FormLabel>{t('searchSites.fields.maxPages')}</FormLabel><NumberInput min={1} max={50} value={value.max_pages} onChange={(_, n) => set('max_pages', Number.isNaN(n) ? 1 : n)}><NumberInputField /></NumberInput></FormControl></HStack><FormControl isRequired><FormLabel>evaluate_pagination</FormLabel><Textarea fontFamily="mono" minH="160px" value={value.evaluate_pagination ?? ''} onChange={(e) => set('evaluate_pagination', e.target.value)} /></FormControl></Stack>}
        </Box>
        <Box bg="white" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={2}>{t('searchSites.sections.extraction')}</Heading><Text color="gray.500" mb={5}>{t('searchSites.hints.js')}</Text>
          <Stack spacing={4}><FormControl isRequired><FormLabel>evaluate_vacancy_list</FormLabel><Textarea fontFamily="mono" minH="220px" value={value.evaluate_vacancy_list} onChange={(e) => set('evaluate_vacancy_list', e.target.value)} /></FormControl><FormControl isRequired><FormLabel>evaluate_vacancy_page</FormLabel><Textarea fontFamily="mono" minH="220px" value={value.evaluate_vacancy_page} onChange={(e) => set('evaluate_vacancy_page', e.target.value)} /></FormControl></Stack>
        </Box>
        <HStack><Button type="submit" colorScheme="purple" isLoading={isSubmitting}>{t('searchSites.save')}</Button><Button onClick={onCancel} isDisabled={isSubmitting}>{t('searchSites.cancel')}</Button></HStack>
      </Stack>
    </Box>
  );
}
