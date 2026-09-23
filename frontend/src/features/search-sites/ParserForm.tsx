import { useEffect, useState, type FormEvent } from 'react';
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
  Radio,
  RadioGroup,
  Select,
  NumberInput,
  NumberInputField,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from '@chakra-ui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { GradientButton } from '@/components/ui/GradientButton';
import { emptyParser, type ParserInput } from './types';

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

type SelectorKind = "data-attr" | "id" | "class" | "tag";

const selectorKind = (value: string): SelectorKind => value.startsWith("[") ? "data-attr" : value.startsWith("#") ? "id" : value.startsWith(".") ? "class" : "tag";
const selectorValue = (value: string, kind: SelectorKind) => kind === "data-attr" ? value.replace(/^\[/, "").replace(/\]$/, "").replace(/=["\x27]?([^"\x27]*)["\x27]?$/, "=$1") : kind === "id" || kind === "class" ? value.slice(1) : value;
const buildSelector = (kind: SelectorKind, value: string) => {
  const clean = value.trim();
  if (kind === "id") return clean ? `#${clean}` : "";
  if (kind === "class") return clean ? `.${clean}` : "";
  if (kind === "data-attr") {
    const [name, ...rest] = clean.split("=");
    const attributeValue = rest.join("=").trim();
    return name.trim() ? (attributeValue ? `[${name.trim()}="${attributeValue}"]` : `[${name.trim()}]`) : "";
  }
  return clean;
};

function SelectorInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [kind, setKind] = useState<SelectorKind>(() => selectorKind(value));

  useEffect(() => {
    setKind(selectorKind(value));
  }, [value]);

  const visibleValue = selectorValue(value, kind);
  return <HStack flex={1}><Select maxW="155px" value={kind} onChange={(e) => { const nextKind = e.currentTarget.value as SelectorKind; setKind(nextKind); onChange(buildSelector(nextKind, visibleValue)); }}><option value="data-attr">data-attr</option><option value="id">id</option><option value="class">class</option><option value="tag">tag</option></Select><Input value={visibleValue} placeholder={kind === "data-attr" ? "data-qa=vacancy-title" : kind === "id" ? "vacancy-title" : kind === "class" ? "vacancy-card" : "article"} onChange={(e) => onChange(buildSelector(kind, e.target.value))} /></HStack>;
}

function SelectorListEditor({ label, tooltip, selectors, onChange }: { label: string; tooltip: string; selectors: string[]; onChange: (selectors: string[]) => void }) {
  return <FormControl isRequired><FieldLabelWithTooltip label={label} tooltip={tooltip} /><Stack spacing={2}>{selectors.map((selector, index) => <HStack key={index}><SelectorInput value={selector} onChange={(next) => onChange(selectors.map((item, itemIndex) => itemIndex === index ? next : item))} /><Button onClick={() => onChange(selectors.filter((_, itemIndex) => itemIndex !== index))} isDisabled={selectors.length === 1}>−</Button></HStack>)}</Stack><FormHelperText>Селекторы проверяются сверху вниз; используется первый непустой результат.</FormHelperText><Button mt={2} size="sm" onClick={() => onChange([...selectors, ""])}>+ fallback</Button></FormControl>;
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
  const selectorConfig = value.extraction_config;
  const set = <K extends keyof ParserInput>(key: K, next: ParserInput[K]) =>
    setValue((current) => ({ ...current, [key]: next }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (value.extraction_engine === 'selectors_v1' && (!selectorConfig?.list.item_selector || selectorConfig.list.fields.title.source.kind !== 'selector' || !selectorConfig.list.fields.title.source.selectors[0] || selectorConfig.detail.fields.job_title.source.kind !== 'selector' || !selectorConfig.detail.fields.job_title.source.selectors[0] || selectorConfig.detail.fields.job_text.source.kind !== 'selector' || !selectorConfig.detail.fields.job_text.source.selectors[0])) return;
    onSubmit({
      ...value,
      extraction_config: value.extraction_engine === 'legacy_js' ? null : value.extraction_config,
      format_url: {
        ...value.format_url,
        query_params: Object.fromEntries(params.filter((item) => item.key.trim()).map((item) => [item.key.trim(), item.value])),
      },
      evaluate_pagination: value.evaluate_pagination || null,
    });
  };

  return (
    <Box as="form" onSubmit={submit} maxW="form">
      <Stack spacing={7}>
        {isInUse && <Alert status="info" borderRadius="xl"><AlertIcon />{t('searchSites.editInUse')}</Alert>}
        {error && <Alert status="error" borderRadius="xl"><AlertIcon />{error}</Alert>}
        <Box bg="surface.raised" p={6} borderRadius="2xl" boxShadow="sm">
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
        <Box bg="surface.raised" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.search')}</Heading>
          <FormControl isRequired mb={4}><FormLabel>{t('searchSites.fields.urlTemplate')}</FormLabel><Input value={value.format_url.url_template} onChange={(e) => set('format_url', { ...value.format_url, url_template: e.target.value })} /><FormHelperText>{t('searchSites.hints.templates')}</FormHelperText></FormControl>
          <FormLabel>{t('searchSites.fields.queryParams')}</FormLabel>
          <Stack spacing={2}>{params.map((item, index) => <HStack key={index}><Input placeholder="key" value={item.key} onChange={(e) => setParams((old) => old.map((row, i) => i === index ? { ...row, key: e.target.value } : row))} /><Input placeholder="value" value={item.value} onChange={(e) => setParams((old) => old.map((row, i) => i === index ? { ...row, value: e.target.value } : row))} /><Button onClick={() => setParams((old) => old.filter((_, i) => i !== index))}>−</Button></HStack>)}</Stack>
          <Button mt={3} size="sm" onClick={() => setParams((old) => [...old, { key: '', value: '' }])}>{t('searchSites.addParam')}</Button>
        </Box>
        <Box bg="surface.raised" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.mode')}</Heading>
          <FormControl mb={4}><FormLabel>{t('searchSites.fields.extractionEngine')}</FormLabel><RadioGroup value={value.extraction_engine} onChange={(next) => { const engine = next as ParserInput['extraction_engine']; setValue((current) => ({ ...current, extraction_engine: engine, fetch_mode: engine === 'legacy_js' ? 'playwright' : current.fetch_mode, extraction_config: engine === 'selectors_v1' ? (current.extraction_config ?? structuredClone(emptyParser.extraction_config)) : current.extraction_config })); }}><HStack><Radio value="selectors_v1">{t('searchSites.fields.selectorsEngine')}</Radio><Radio value="legacy_js">{t('searchSites.fields.legacyEngine')}</Radio></HStack></RadioGroup></FormControl>
          <FormControl><FormLabel>{t('searchSites.fields.fetchMode')}</FormLabel><Select value={value.fetch_mode} onChange={(e) => set('fetch_mode', e.target.value as ParserInput['fetch_mode'])} isDisabled={value.extraction_engine === 'legacy_js'}><option value="http">{t('searchSites.fields.http')}</option><option value="playwright">{t('searchSites.fields.playwright')}</option></Select></FormControl>
        </Box>
        <Box bg="surface.raised" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={5}>{t('searchSites.sections.pagination')}</Heading>
          <Checkbox isChecked={value.has_pagination} onChange={(e) => set('has_pagination', e.target.checked)}>{t('searchSites.fields.hasPagination')}</Checkbox>
          {value.has_pagination && <Stack mt={4} spacing={4}><HStack><FormControl><FormLabel>{t('searchSites.fields.paginationStart')}</FormLabel><NumberInput min={0} value={value.pagination_start} onChange={(_, n) => set('pagination_start', Number.isNaN(n) ? 0 : n)}><NumberInputField /></NumberInput></FormControl><FormControl><FormLabel>{t('searchSites.fields.maxPages')}</FormLabel><NumberInput min={1} max={50} value={value.max_pages} onChange={(_, n) => set('max_pages', Number.isNaN(n) ? 1 : n)}><NumberInputField /></NumberInput></FormControl></HStack>{value.extraction_engine === 'selectors_v1' && selectorConfig ? <FormControl isRequired><FieldLabelWithTooltip label="Номера страниц" tooltip="Элементы пагинации, текст которых содержит номер страницы. Пример: data-qa=pager-page, class page или tag a." /><SelectorInput value={selectorConfig.pagination?.selectors[0] ?? ""} onChange={(selector) => set("extraction_config", { ...selectorConfig, pagination: { enabled: true, selectors: [selector], extract: "text", transforms: [{ kind: "regex", pattern: "\\d+", group: 0 }] } })} /><FormHelperText>Из текста будет извлечено число регулярным выражением \d+.</FormHelperText></FormControl> : <FormControl isRequired><FormLabel>evaluate_pagination</FormLabel><Textarea fontFamily="mono" minH="160px" value={value.evaluate_pagination ?? ''} onChange={(e) => set('evaluate_pagination', e.target.value)} /></FormControl>}</Stack>}
        </Box>
        <Box bg="surface.raised" p={6} borderRadius="2xl" boxShadow="sm">
          <Heading size="md" mb={2}>{t('searchSites.sections.extraction')}</Heading>
          {value.extraction_engine === 'selectors_v1' && selectorConfig ? <Stack spacing={4}>
            <FormControl isRequired><FieldLabelWithTooltip label={t('searchSites.fields.itemSelector')} tooltip="Корневой элемент одной карточки вакансии. Все title/link selectors ищутся внутри него. Пример: data-qa=vacancy-serp__vacancy или class vacancy-card." /><SelectorInput value={selectorConfig.list.item_selector} onChange={(item_selector) => set('extraction_config', { ...selectorConfig, list: { ...selectorConfig.list, item_selector } })} /></FormControl>
            <SelectorListEditor label="Заголовок вакансии (title)" tooltip="Элемент заголовка внутри карточки. Примеры: data-qa=serp-item__title-text, class vacancy-title, tag h2." selectors={selectorConfig.list.fields.title.source.kind === "selector" ? selectorConfig.list.fields.title.source.selectors : [""]} onChange={(selectors) => set("extraction_config", { ...selectorConfig, list: { ...selectorConfig.list, fields: { ...selectorConfig.list.fields, title: { ...selectorConfig.list.fields.title, source: { kind: "selector", selectors, extract: "text" } } } } })} />
            <SelectorListEditor label="Ссылка на вакансию (link)" tooltip="Ссылка внутри карточки. Обычно data-qa=serp-item__title или tag a. Из атрибута href будет построен абсолютный URL." selectors={selectorConfig.list.fields.link.source.kind === "selector" ? selectorConfig.list.fields.link.source.selectors : [""]} onChange={(selectors) => set("extraction_config", { ...selectorConfig, list: { ...selectorConfig.list, fields: { ...selectorConfig.list.fields, link: { ...selectorConfig.list.fields.link, source: { kind: "selector", selectors, extract: "attribute", attribute: "href", absolute_url: true } } } } })} />
            <Box borderWidth="1px" borderRadius="xl" p={4}><Text fontWeight="semibold" mb={3}>vacancy_id из поля link</Text><HStack><FormControl isRequired><FieldLabelWithTooltip label="Регулярное выражение" tooltip="Из абсолютной ссылки извлекается vacancy_id. Пример /vacancy/(\d+) и группа 1 вернут 123 из /vacancy/123." /><Input value={selectorConfig.list.fields.vacancy_id.transforms[0]?.pattern ?? ""} onChange={(e) => set("extraction_config", { ...selectorConfig, list: { ...selectorConfig.list, fields: { ...selectorConfig.list.fields, vacancy_id: { ...selectorConfig.list.fields.vacancy_id, source: { kind: "field", field: "link" }, transforms: [{ kind: "regex", pattern: e.target.value, group: selectorConfig.list.fields.vacancy_id.transforms[0]?.group ?? 1 }] } } } })} /></FormControl><FormControl maxW="130px"><FormLabel>Группа</FormLabel><NumberInput min={0} value={selectorConfig.list.fields.vacancy_id.transforms[0]?.group ?? 1} onChange={(_, group) => set("extraction_config", { ...selectorConfig, list: { ...selectorConfig.list, fields: { ...selectorConfig.list.fields, vacancy_id: { ...selectorConfig.list.fields.vacancy_id, source: { kind: "field", field: "link" }, transforms: [{ kind: "regex", pattern: selectorConfig.list.fields.vacancy_id.transforms[0]?.pattern ?? "", group: Number.isNaN(group) ? 1 : group }] } } } })}><NumberInputField /></NumberInput></FormControl></HStack></Box>
            <Heading size="sm">Данные одной вакансии</Heading>
            <SelectorListEditor label="Заголовок страницы вакансии (job_title)" tooltip="Заголовок на странице одной вакансии. Часто tag h1 или data-qa=vacancy-title." selectors={selectorConfig.detail.fields.job_title.source.kind === "selector" ? selectorConfig.detail.fields.job_title.source.selectors : [""]} onChange={(selectors) => set("extraction_config", { ...selectorConfig, detail: { ...selectorConfig.detail, fields: { ...selectorConfig.detail.fields, job_title: { ...selectorConfig.detail.fields.job_title, source: { kind: "selector", selectors, extract: "text" } } } } })} />
            <SelectorListEditor label="Описание вакансии (job_text)" tooltip="Основной текст вакансии. Часто data-qa=vacancy-description, tag article или tag main." selectors={selectorConfig.detail.fields.job_text.source.kind === "selector" ? selectorConfig.detail.fields.job_text.source.selectors : [""]} onChange={(selectors) => set("extraction_config", { ...selectorConfig, detail: { ...selectorConfig.detail, fields: { ...selectorConfig.detail.fields, job_text: { ...selectorConfig.detail.fields.job_text, source: { kind: "selector", selectors, extract: "text" } } } } })} />
            {selectorConfig.detail.fields.company_name ? <Box><SelectorListEditor label="Название компании (company_name)" tooltip="Необязательное поле компании. Оставьте блок удалённым, если сайт его не предоставляет." selectors={selectorConfig.detail.fields.company_name.source.kind === "selector" ? selectorConfig.detail.fields.company_name.source.selectors : [""]} onChange={(selectors) => set("extraction_config", { ...selectorConfig, detail: { ...selectorConfig.detail, fields: { ...selectorConfig.detail.fields, company_name: { ...selectorConfig.detail.fields.company_name!, source: { kind: "selector", selectors, extract: "text" } } } } })} /><Button mt={2} size="sm" colorScheme="red" variant="ghost" onClick={() => { const { company_name, ...fields } = selectorConfig.detail.fields; set("extraction_config", { ...selectorConfig, detail: { ...selectorConfig.detail, fields } }); }}>Удалить название компании</Button></Box> : <Button alignSelf="flex-start" onClick={() => set("extraction_config", { ...selectorConfig, detail: { ...selectorConfig.detail, fields: { ...selectorConfig.detail.fields, company_name: { source: { kind: "selector", selectors: [""], extract: "text" }, required: false, normalize: { strip: true, collapse_whitespace: true }, transforms: [] } } } })}>+ Добавить название компании</Button>}
          </Stack> : <><Text color="text.muted" mb={5}>{t('searchSites.hints.js')}</Text><Stack spacing={4}><FormControl isRequired><FormLabel>evaluate_vacancy_list</FormLabel><Textarea fontFamily="mono" minH="220px" value={value.evaluate_vacancy_list} onChange={(e) => set('evaluate_vacancy_list', e.target.value)} /></FormControl><FormControl isRequired><FormLabel>evaluate_vacancy_page</FormLabel><Textarea fontFamily="mono" minH="220px" value={value.evaluate_vacancy_page} onChange={(e) => set('evaluate_vacancy_page', e.target.value)} /></FormControl></Stack></>}
        </Box>
        <HStack>
          <GradientButton type="submit" isLoading={isSubmitting}>
            {t('searchSites.save')}
          </GradientButton>
          <Button variant="danger" onClick={onCancel} isDisabled={isSubmitting}>{t('searchSites.cancel')}</Button>
        </HStack>
      </Stack>
    </Box>
  );
}
