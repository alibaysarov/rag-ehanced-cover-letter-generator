import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  FormLabel,
  HStack,
  IconButton,
  Input,
  VStack,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { AnimatePresence, motion } from 'framer-motion';

interface AnimatedListInputProps {
  label: string;
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

interface Row {
  id: string;
  value: string;
}

const makeId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

const toRows = (values: string[]): Row[] =>
  values.map((v) => ({ id: makeId(), value: v }));

const AnimatedListInput: React.FC<AnimatedListInputProps> = ({
  label,
  values,
  onChange,
  placeholder,
}) => {
  const [rows, setRows] = useState<Row[]>(() => toRows(values));
  const lastEmitted = useRef<string[]>(values);
  const inputRefs = useRef<Map<string, HTMLInputElement>>(new Map());
  const pendingFocusId = useRef<string | null>(null);

  useEffect(() => {
    const same =
      values.length === lastEmitted.current.length &&
      values.every((v, i) => v === lastEmitted.current[i]);
    if (!same) {
      setRows(toRows(values));
      lastEmitted.current = values;
    }
  }, [values]);

  const emit = (next: Row[]) => {
    setRows(next);
    const plain = next.map((r) => r.value);
    lastEmitted.current = plain;
    onChange(plain);
  };

  useEffect(() => {
    if (pendingFocusId.current) {
      const el = inputRefs.current.get(pendingFocusId.current);
      if (el) {
        el.focus();
        pendingFocusId.current = null;
      }
    }
  });

  const handleAdd = () => {
    const newId = makeId();
    pendingFocusId.current = newId;
    emit([...rows, { id: newId, value: '' }]);
  };

  const handleRemove = (id: string) => {
    emit(rows.filter((r) => r.id !== id));
  };

  const handleChange = (id: string, value: string) => {
    emit(rows.map((r) => (r.id === id ? { ...r, value } : r)));
  };

  return (
    <Box w="100%">
      <HStack justify="space-between" mb={2}>
        <FormLabel m={0}>{label}</FormLabel>
        <Button
          size="sm"
          leftIcon={<AddIcon boxSize={3} />}
          onClick={handleAdd}
          variant="outline"
          colorScheme="blue"
        >
          Добавить
        </Button>
      </HStack>
      <VStack spacing={2} align="stretch">
        <AnimatePresence initial={false}>
          {rows.map((row) => (
            <motion.div
              key={row.id}
              initial={{ opacity: 0, x: -20, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              exit={{ opacity: 0, x: 20, height: 0 }}
              transition={{ duration: 0.2 }}
              style={{ overflow: 'hidden' }}
            >
              <HStack>
                <Input
                  ref={(el) => {
                    if (el) inputRefs.current.set(row.id, el);
                    else inputRefs.current.delete(row.id);
                  }}
                  value={row.value}
                  onChange={(e) => handleChange(row.id, e.target.value)}
                  placeholder={placeholder}
                />
                <IconButton
                  aria-label="Удалить"
                  icon={<DeleteIcon />}
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => handleRemove(row.id)}
                />
              </HStack>
            </motion.div>
          ))}
        </AnimatePresence>
      </VStack>
    </Box>
  );
};

export default AnimatedListInput;
