import { useEffect, useRef, useState } from 'react';
import {
  Box,
  Flex,
  Grid,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Portal,
  Text,
} from '@chakra-ui/react';
import { IconCalendar, IconChevronLeft, IconChevronRight } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

function toYMD(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function parseYMD(s: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!match) return null;
  const d = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return isNaN(d.getTime()) ? null : d;
}

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
}

function startOfMonth(year: number, month: number): Date {
  return new Date(year, month, 1);
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

// Returns 0=Mon ... 6=Sun offset for the first day of the month
function firstDayOffset(year: number, month: number): number {
  const jsDay = startOfMonth(year, month).getDay(); // 0=Sun
  return jsDay === 0 ? 6 : jsDay - 1;
}

interface CalendarProps {
  from: Date | null;
  to: Date | null;
  activeInput: 'from' | 'to';
  onSelect: (date: Date) => void;
}

function Calendar({ from, to, activeInput, onSelect }: CalendarProps) {
  const { t } = useTranslation();
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  const weekDays = t('datePicker.weekDays', { returnObjects: true }) as string[];
  const months = t('datePicker.months', { returnObjects: true }) as string[];

  const days = daysInMonth(viewYear, viewMonth);
  const offset = firstDayOffset(viewYear, viewMonth);
  const cells: (number | null)[] = [
    ...Array(offset).fill(null),
    ...Array.from({ length: days }, (_, i) => i + 1),
  ];
  // Pad to complete 6-week grid
  while (cells.length % 7 !== 0) cells.push(null);

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11); }
    else setViewMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0); }
    else setViewMonth(m => m + 1);
  };

  const isInRange = (day: number) => {
    if (!from || !to || !day) return false;
    const d = new Date(viewYear, viewMonth, day);
    return d > from && d < to;
  };

  const isFrom = (day: number) =>
    !!from && sameDay(from, new Date(viewYear, viewMonth, day));

  const isTo = (day: number) =>
    !!to && sameDay(to, new Date(viewYear, viewMonth, day));

  const isToday = (day: number) =>
    sameDay(today, new Date(viewYear, viewMonth, day));

  return (
    <Box
      bg="white"
      border="1px solid"
      borderColor="rgba(226,232,240,0.8)"
      borderRadius="2xl"
      boxShadow="0 16px 48px rgba(15,23,42,0.12), 0 4px 16px rgba(99,102,241,0.08)"
      p={4}
      minW="300px"
      sx={{
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
      }}
    >
      {/* Month navigation */}
      <Flex align="center" justify="space-between" mb={3}>
        <IconButton
          aria-label={t('datePicker.prevMonth')}
          icon={<IconChevronLeft size={16} stroke={2} />}
          size="xs"
          variant="ghost"
          color="slate.500"
          onClick={prevMonth}
          _hover={{ color: 'aurora.indigo', bg: 'rgba(99,102,241,0.08)' }}
          borderRadius="lg"
        />
        <Text fontSize="sm" fontWeight={600} color="slate.800">
          {months[viewMonth]} {viewYear}
        </Text>
        <IconButton
          aria-label={t('datePicker.nextMonth')}
          icon={<IconChevronRight size={16} stroke={2} />}
          size="xs"
          variant="ghost"
          color="slate.500"
          onClick={nextMonth}
          _hover={{ color: 'aurora.indigo', bg: 'rgba(99,102,241,0.08)' }}
          borderRadius="lg"
        />
      </Flex>

      {/* Weekday headers */}
      <Grid templateColumns="repeat(7, 1fr)" mb={1}>
        {weekDays.map((d) => (
          <Flex key={d} justify="center" align="center" h="28px">
            <Text fontSize="xs" fontWeight={600} color="slate.400">
              {d}
            </Text>
          </Flex>
        ))}
      </Grid>

      {/* Day cells */}
      <Grid templateColumns="repeat(7, 1fr)" gap={0.5}>
        {cells.map((day, idx) => {
          if (!day) return <Box key={idx} h="34px" />;
          const fromDay = isFrom(day);
          const toDay = isTo(day);
          const inRange = isInRange(day);
          const todayDay = isToday(day);
          const highlighted = fromDay || toDay;

          return (
            <Flex
              key={idx}
              as="button"
              type="button"
              justify="center"
              align="center"
              h="34px"
              borderRadius={highlighted ? 'xl' : 'lg'}
              fontSize="sm"
              fontWeight={highlighted ? 700 : todayDay ? 600 : 400}
              color={highlighted ? 'white' : inRange ? 'aurora.indigo' : todayDay ? 'aurora.indigo' : 'slate.700'}
              bg={
                highlighted
                  ? 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)'
                  : inRange
                  ? 'rgba(99,102,241,0.1)'
                  : 'transparent'
              }
              boxShadow={highlighted ? '0 4px 12px rgba(99,102,241,0.3)' : undefined}
              transition="all 150ms ease"
              _hover={{
                bg: highlighted
                  ? 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)'
                  : 'rgba(99,102,241,0.12)',
                color: highlighted ? 'white' : 'aurora.indigo',
              }}
              onClick={() => onSelect(new Date(viewYear, viewMonth, day))}
              position="relative"
            >
              {todayDay && !highlighted && (
                <Box
                  position="absolute"
                  bottom="3px"
                  left="50%"
                  transform="translateX(-50%)"
                  w="4px"
                  h="4px"
                  borderRadius="full"
                  bg="aurora.indigo"
                />
              )}
              {day}
            </Flex>
          );
        })}
      </Grid>

      {/* Hint */}
      <Text mt={3} fontSize="xs" color="slate.400" textAlign="center">
        {activeInput === 'from' ? t('datePicker.selectFrom') : t('datePicker.selectTo')}
      </Text>
    </Box>
  );
}

export interface DateRange {
  from: string;
  to: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const { t } = useTranslation();
  const [activeInput, setActiveInput] = useState<'from' | 'to' | null>(null);
  const [fromInput, setFromInput] = useState(value.from);
  const [toInput, setToInput] = useState(value.to);
  const containerRef = useRef<HTMLDivElement>(null);
  const [calendarPos, setCalendarPos] = useState({ top: 0, left: 0 });

  // Sync controlled value → local input strings when parent changes
  useEffect(() => { setFromInput(value.from); }, [value.from]);
  useEffect(() => { setToInput(value.to); }, [value.to]);

  // Close on outside click
  useEffect(() => {
    if (!activeInput) return;
    const handler = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        // Check if click is on the calendar portal
        const portal = document.getElementById('date-range-calendar-portal');
        if (portal?.contains(e.target as Node)) return;
        setActiveInput(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [activeInput]);

  const openCalendar = (which: 'from' | 'to') => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setCalendarPos({
        top: rect.bottom + window.scrollY + 8,
        left: rect.left + window.scrollX,
      });
    }
    setActiveInput(which);
  };

  const handleSelect = (date: Date) => {
    const ymd = toYMD(date);
    if (activeInput === 'from') {
      setFromInput(ymd);
      onChange({ ...value, from: ymd });
      setActiveInput('to');
    } else {
      setToInput(ymd);
      onChange({ ...value, to: ymd });
      setActiveInput(null);
    }
  };

  const handleFromInput = (v: string) => {
    setFromInput(v);
    const d = parseYMD(v);
    if (d) onChange({ ...value, from: v });
  };

  const handleToInput = (v: string) => {
    setToInput(v);
    const d = parseYMD(v);
    if (d) onChange({ ...value, to: v });
  };

  const fromDate = parseYMD(value.from);
  const toDate = parseYMD(value.to);

  const inputSx = {
    bg: 'rgba(255,255,255,0.6)',
    border: '1px solid rgba(226,232,240,0.8)',
    borderRadius: 'xl',
    fontSize: 'sm',
    color: 'slate.700',
    _focus: {
      border: '1px solid rgba(99,102,241,0.5)',
      boxShadow: '0 0 0 3px rgba(99,102,241,0.12)',
    },
    _placeholder: { color: 'slate.400' },
  };

  return (
    <Box ref={containerRef} position="relative">
      <Flex gap={3} align="center" flexWrap="wrap">
        <Box>
          <Text fontSize="xs" fontWeight={500} color="slate.500" mb={1}>
            {t('datePicker.from')}
          </Text>
          <InputGroup size="sm" w="160px">
            <InputLeftElement pointerEvents="none" color="slate.400" h="full">
              <IconCalendar size={14} stroke={1.75} />
            </InputLeftElement>
            <Input
              value={fromInput}
              onChange={(e) => handleFromInput(e.target.value)}
              onFocus={() => openCalendar('from')}
              placeholder={t('datePicker.placeholder')}
              sx={inputSx}
              pl={8}
            />
          </InputGroup>
        </Box>

        <Text color="slate.300" mt={5} fontSize="sm">—</Text>

        <Box>
          <Text fontSize="xs" fontWeight={500} color="slate.500" mb={1}>
            {t('datePicker.to')}
          </Text>
          <InputGroup size="sm" w="160px">
            <InputLeftElement pointerEvents="none" color="slate.400" h="full">
              <IconCalendar size={14} stroke={1.75} />
            </InputLeftElement>
            <Input
              value={toInput}
              onChange={(e) => handleToInput(e.target.value)}
              onFocus={() => openCalendar('to')}
              placeholder={t('datePicker.placeholder')}
              sx={inputSx}
              pl={8}
            />
          </InputGroup>
        </Box>
      </Flex>

      {activeInput && (
        <Portal>
          <Box
            id="date-range-calendar-portal"
            position="absolute"
            top={`${calendarPos.top}px`}
            left={`${calendarPos.left}px`}
            zIndex={1500}
          >
            <Calendar
              from={fromDate}
              to={toDate}
              activeInput={activeInput}
              onSelect={handleSelect}
            />
          </Box>
        </Portal>
      )}
    </Box>
  );
}

export default DateRangePicker;
