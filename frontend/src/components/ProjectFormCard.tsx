import React from 'react';
import {
  Box,
  Card,
  CardBody,
  Checkbox,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  HStack,
  IconButton,
  Input,
  Select,
  SimpleGrid,
  VStack,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import AnimatedListInput from './AnimatedListInput';

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 1950 + 3 }, (_, i) => currentYear + 2 - i);

const yearSelectSx = {
  bg: 'rgba(255,255,255,0.6)',
  border: '1px solid',
  borderColor: 'rgba(226,232,240,0.8)',
  borderRadius: 'xl',
  fontSize: 'sm',
  color: 'slate.700',
  cursor: 'pointer',
  _focus: {
    borderColor: 'rgba(99,102,241,0.5)',
    boxShadow: '0 0 0 3px rgba(99,102,241,0.12)',
  },
  _hover: {
    borderColor: 'rgba(99,102,241,0.35)',
  },
  _disabled: {
    opacity: 0.45,
    cursor: 'not-allowed',
  },
};

export interface ProjectInput {
  name: string;
  website: string;
  start_month: number | '';
  start_year: number | '';
  end_month: number | '';
  end_year: number | '';
  currently_working: boolean;
  skills: string[];
  achievements: string[];
  technologies: string[];
}

export const emptyProject = (): ProjectInput => ({
  name: '',
  website: '',
  start_month: '',
  start_year: '',
  end_month: '',
  end_year: '',
  currently_working: false,
  skills: [],
  achievements: [],
  technologies: [],
});

interface ProjectFormCardProps {
  value: ProjectInput;
  onChange: (next: ProjectInput) => void;
  onRemove?: () => void;
  index?: number;
  nameError?: string;
}

const ProjectFormCard: React.FC<ProjectFormCardProps> = ({
  value,
  onChange,
  onRemove,
  index,
  nameError,
}) => {
  const { t } = useTranslation();
  const months = t('projectForm.months', { returnObjects: true }) as string[];

  const update = <K extends keyof ProjectInput>(key: K, v: ProjectInput[K]) => {
    onChange({ ...value, [key]: v });
  };

  const handleCurrentlyWorking = (checked: boolean) => {
    onChange({ ...value, currently_working: checked, end_month: '', end_year: '' });
  };

  const heading =
    typeof index === 'number'
      ? t('projectForm.projectN', { n: index + 1 })
      : t('projectForm.project');

  return (
    <Card variant="outline">
      <CardBody>
        <HStack justify="space-between" mb={3} align="start">
          <Heading size="sm">{heading}</Heading>
          {onRemove && (
            <IconButton
              aria-label={t('projectForm.deleteAriaLabel')}
              icon={<CloseIcon boxSize={3} />}
              size="sm"
              variant="ghost"
              colorScheme="red"
              onClick={onRemove}
            />
          )}
        </HStack>
        <VStack spacing={4} align="stretch">
          <FormControl isInvalid={!!nameError} isRequired>
            <FormLabel>{t('projectForm.name')}</FormLabel>
            <Input
              value={value.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="LOKALI APP"
            />
            <FormErrorMessage>{nameError}</FormErrorMessage>
          </FormControl>

          <FormControl>
            <FormLabel>{t('projectForm.website')}</FormLabel>
            <Input
              value={value.website}
              onChange={(e) => update('website', e.target.value)}
              placeholder="https://example.com"
              type="url"
            />
          </FormControl>

          <Box>
            <FormLabel mb={2}>{t('projectForm.startDate')}</FormLabel>
            <SimpleGrid columns={2} spacing={3} mb={2}>
              <FormControl>
                <FormLabel fontSize="xs" color="gray.500" mb={1}>
                  {t('projectForm.startDate')}
                </FormLabel>
                <HStack spacing={2}>
                  <Select
                    placeholder="Месяц"
                    size="sm"
                    value={value.start_month}
                    onChange={(e) =>
                      update('start_month', e.target.value ? Number(e.target.value) : '')
                    }
                  >
                    {months.map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </Select>
                  <Select
                    size="sm"
                    placeholder="Год"
                    value={value.start_year}
                    onChange={(e) => update('start_year', e.target.value ? Number(e.target.value) : '')}
                    sx={yearSelectSx}
                  >
                    {YEARS.map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </Select>
                </HStack>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="xs" color="gray.500" mb={1}>
                  {t('projectForm.endDate')}
                </FormLabel>
                <HStack spacing={2}>
                  <Select
                    placeholder="Месяц"
                    size="sm"
                    isDisabled={value.currently_working}
                    value={value.end_month}
                    onChange={(e) =>
                      update('end_month', e.target.value ? Number(e.target.value) : '')
                    }
                  >
                    {months.map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </Select>
                  <Select
                    size="sm"
                    placeholder="Год"
                    isDisabled={value.currently_working}
                    value={value.end_year}
                    onChange={(e) => update('end_year', e.target.value ? Number(e.target.value) : '')}
                    sx={yearSelectSx}
                  >
                    {YEARS.map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </Select>
                </HStack>
              </FormControl>
            </SimpleGrid>

            <Checkbox
              isChecked={value.currently_working}
              onChange={(e) => handleCurrentlyWorking(e.target.checked)}
              size="sm"
            >
              {t('projectForm.currentlyWorking')}
            </Checkbox>
          </Box>

          <Box>
            <AnimatedListInput
              label={t('projectForm.skills')}
              values={value.skills}
              onChange={(v) => update('skills', v)}
              placeholder="проектирование REST API"
            />
          </Box>

          <Box>
            <AnimatedListInput
              label={t('projectForm.achievements')}
              values={value.achievements}
              onChange={(v) => update('achievements', v)}
              placeholder="Создал REST API для мобильного приложения"
            />
          </Box>

          <Box>
            <AnimatedListInput
              label={t('projectForm.technologies')}
              values={value.technologies}
              onChange={(v) => update('technologies', v)}
              placeholder="Node.js"
            />
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default ProjectFormCard;
