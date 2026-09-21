import { Alert, AlertIcon, Box, Heading, Spinner } from '@chakra-ui/react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { ParserForm } from '@/features/search-sites/ParserForm';
import { useParserDetail, useUpdateParser } from '@/features/search-sites/hooks';

const message = (error: unknown, fallback: string) => {
  const detail = (error as { response?: { data?: { detail?: string | { message?: string } } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : detail?.message || fallback;
};

export default function EditSearchSitePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { id = '0' } = useParams();
  const parserId = Number(id);
  const [search] = useSearchParams();
  const detail = useParserDetail(user?.id ?? 0, parserId);
  const mutation = useUpdateParser(user?.id ?? 0, parserId);
  const returnUrl = `/search-sites?page=${search.get('return_page') || '1'}&page_size=${search.get('return_page_size') || '20'}`;
  if (detail.isLoading) return <Spinner />;
  if (!detail.data) return <Alert status="error"><AlertIcon />{t('searchSites.loadError')}</Alert>;
  const { id: _id, site_key: _siteKey, version, created_at: _created, updated_at: _updated, is_in_use, can_delete: _canDelete, ...initial } = detail.data;
  return <Box><Heading size="lg" mb={7}>{t('searchSites.editTitle')}</Heading><ParserForm initial={initial} isInUse={is_in_use} isSubmitting={mutation.isPending} error={mutation.error ? message(mutation.error, t('searchSites.saveError')) : undefined} onCancel={() => navigate(returnUrl)} onSubmit={async (value) => { await mutation.mutateAsync({ data: value, version }); navigate(returnUrl); }} /></Box>;
}
