import { Box, Heading } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { ParserForm } from '@/features/search-sites/ParserForm';
import { useCreateParser } from '@/features/search-sites/hooks';
import { emptyParser } from '@/features/search-sites/types';

const message = (error: unknown, fallback: string) => {
  const detail = (error as { response?: { data?: { detail?: string | { message?: string } } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : detail?.message || fallback;
};

export default function NewSearchSitePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const mutation = useCreateParser(user?.id ?? 0);
  return <Box><Heading size="lg" mb={7}>{t('searchSites.newTitle')}</Heading><ParserForm initial={emptyParser} isSubmitting={mutation.isPending} error={mutation.error ? message(mutation.error, t('searchSites.saveError')) : undefined} onCancel={() => navigate('/search-sites')} onSubmit={async (value) => { await mutation.mutateAsync(value); navigate('/search-sites?page=1&page_size=20'); }} /></Box>;
}
