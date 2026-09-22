import { useId } from 'react'
import {
  Box,
  Flex,
  FormControl,
  FormLabel,
  Input,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Text,
} from '@chakra-ui/react'
import { useTranslation } from 'react-i18next'

const MIN_VACANCIES = 1
const MAX_VACANCIES = 1000
export const DEFAULT_VACANCY_LIMIT = '100'

export function isValidVacancyLimit(value: string) {
  const count = Number(value)
  return Number.isInteger(count) && count >= MIN_VACANCIES && count <= MAX_VACANCIES
}

interface VacancyLimitControlProps {
  value: string
  onChange: (value: string) => void
  isDisabled: boolean
}

export function VacancyLimitControl({ value, onChange, isDisabled }: VacancyLimitControlProps) {
  const { t } = useTranslation()
  const id = useId()
  const labelId = `${id}-label`
  const hintId = `${id}-hint`
  const count = Number(value)
  const sliderValue = Number.isFinite(count)
    ? Math.min(MAX_VACANCIES, Math.max(MIN_VACANCIES, count))
    : MIN_VACANCIES

  return (
    <FormControl mt={5} isDisabled={isDisabled}>
      <Flex align="center" justify="space-between" gap={4} mb={2}>
        <FormLabel id={labelId} htmlFor={id} m={0} fontSize="sm" fontWeight={600}>
          {t('autoParse.vacancyLimit')}
        </FormLabel>
        <Input
          id={id}
          name="vacancy_limit"
          type="number"
          inputMode="numeric"
          min={MIN_VACANCIES}
          max={MAX_VACANCIES}
          step={1}
          required
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={hintId}
          w="100px"
          flexShrink={0}
          height={9}
          fontSize="sm"
          fontWeight={600}
          textAlign="center"
          color="text.primary"
          bg="surface.raised"
          borderColor="rgba(226,232,240,0.8)"
          borderRadius="xl"
          focusBorderColor="aurora.indigo"
        />
      </Flex>
      <Box px={2}>
        <Slider
          min={MIN_VACANCIES}
          max={MAX_VACANCIES}
          step={1}
          value={sliderValue}
          onChange={(next) => onChange(String(next))}
          isDisabled={isDisabled}
          aria-labelledby={labelId}
          aria-describedby={hintId}
          focusThumbOnChange={false}
        >
          <SliderTrack bg="rgba(226,232,240,0.7)" h={1.5} borderRadius="full">
            <SliderFilledTrack bgGradient="linear(to-r, aurora.indigo, purple.400)" />
          </SliderTrack>
          <SliderThumb boxSize={4} border="2px solid" borderColor="aurora.indigo" />
        </Slider>
      </Box>
      <Flex justify="space-between" fontSize="xs" color="text.muted" mt={1}>
        <Text>{MIN_VACANCIES}</Text>
        <Text>{MAX_VACANCIES}</Text>
      </Flex>
      <Text id={hintId} mt={1} fontSize="xs" color="text.muted">
        {t('autoParse.vacancyLimitHint')}
      </Text>
    </FormControl>
  )
}
