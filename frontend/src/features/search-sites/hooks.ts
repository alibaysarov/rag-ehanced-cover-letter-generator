import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { parserApi } from './api';
import type { ParserInput } from './types';

export const parserKeys = {
  all: (userId: number) => ['parsers', userId] as const,
  lists: (userId: number) => ['parsers', userId, 'list'] as const,
  list: (userId: number, page: number, pageSize: number) =>
    ['parsers', userId, 'list', page, pageSize] as const,
  detail: (userId: number, id: number) => ['parsers', userId, 'detail', id] as const,
};

export const useParserList = (userId: number, page: number, pageSize: number) =>
  useQuery({
    queryKey: parserKeys.list(userId, page, pageSize),
    queryFn: () => parserApi.list(page, pageSize),
    enabled: userId > 0,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
  });

export const useParserDetail = (userId: number, id: number) =>
  useQuery({
    queryKey: parserKeys.detail(userId, id),
    queryFn: () => parserApi.detail(id),
    enabled: userId > 0 && id > 0,
  });

export const useCreateParser = (userId: number) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: ParserInput) => parserApi.create(data),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: parserKeys.lists(userId), refetchType: 'all' });
    },
  });
};

export const useUpdateParser = (userId: number, id: number) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ data, version }: { data: ParserInput; version: number }) =>
      parserApi.update(id, data, version),
    onSuccess: async (saved) => {
      client.setQueryData(parserKeys.detail(userId, id), saved);
      await client.invalidateQueries({ queryKey: parserKeys.lists(userId), refetchType: 'all' });
    },
  });
};

export const useDeleteParser = (userId: number) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => parserApi.remove(id),
    onSuccess: async (_, id) => {
      client.removeQueries({ queryKey: parserKeys.detail(userId, id) });
      await client.invalidateQueries({ queryKey: parserKeys.lists(userId), refetchType: 'all' });
    },
  });
};
