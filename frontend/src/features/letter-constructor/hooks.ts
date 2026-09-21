import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { letterConstructorApi as api } from './api';
import type { PhraseType, TemplateCase, TemplateStatus } from './types';

export function useDebouncedValue<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const timer = window.setTimeout(() => setDebounced(value), delay); return () => window.clearTimeout(timer); }, [value, delay]);
  return debounced;
}
export const constructorKeys = { root: ['letter-constructor'] as const, phrases: ['letter-constructor', 'phrases'] as const, templates: ['letter-constructor', 'templates'] as const };
export const usePhrases = (params: { q?: string; type?: PhraseType; is_active?: boolean; page: number; page_size: number }) =>
  useQuery({ queryKey: [...constructorKeys.phrases, params], queryFn: () => api.phrases(params) });
export const useTemplates = (params: { q?: string; case?: TemplateCase; status?: TemplateStatus; page: number; page_size: number }) =>
  useQuery({ queryKey: [...constructorKeys.templates, params], queryFn: () => api.templates(params) });
export const useConstructorMutation = <T,>(mutationFn: (value: T) => Promise<unknown>) => {
  const client = useQueryClient();
  return useMutation({ mutationFn, onSuccess: () => client.invalidateQueries({ queryKey: constructorKeys.root }) });
};
