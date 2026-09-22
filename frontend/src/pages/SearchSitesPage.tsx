import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Select,
  Spinner,
  Stack,
  Text,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { GradientButton } from '@/components/ui/GradientButton';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useDeleteParser, useParserList } from '@/features/search-sites/hooks';

const purpleOutline = {
  color: 'aurora.indigo',
  borderColor: 'rgba(0, 123, 255, 0.5)',
  bg: 'rgba(0, 123, 255, 0.05)',
  _hover: {
    color: 'white',
    borderColor: 'transparent',
    bg: 'aurora.indigo',
    boxShadow: '0 5px 16px rgba(0, 123, 255, 0.3)',
    _disabled: { color: 'aurora.indigo', bg: 'rgba(0, 123, 255, 0.05)' },
  },
  _active: { bg: '#0069D9' },
  _disabled: { opacity: 0.35, cursor: 'not-allowed' },
};

const apiMessage = (error: unknown, fallback: string) => {
  const detail = (error as { response?: { data?: { detail?: string | { message?: string } } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : detail?.message || fallback;
};

export default function SearchSitesPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [search, setSearch] = useSearchParams();
  const page = Math.max(1, Number(search.get('page')) || 1);
  const pageSize = Math.min(100, Math.max(1, Number(search.get('page_size')) || 20));
  const query = useParserList(user?.id ?? 0, page, pageSize);
  const remove = useDeleteParser(user?.id ?? 0);
  const pages = Math.max(1, Math.ceil((query.data?.total ?? 0) / pageSize));

  const setPage = (next: number, nextSize = pageSize) =>
    setSearch({ page: String(next), page_size: String(nextSize) });
  const deleteItem = async (id: number, name: string) => {
    if (!window.confirm(t('searchSites.confirmDelete', { name }))) return;
    try {
      await remove.mutateAsync(id);
      const isLast = query.data?.items.length === 1;
      if (isLast && page > 1) setPage(page - 1);
    } catch (error) {
      toast({ status: 'error', title: apiMessage(error, t('searchSites.deleteError')) });
      await query.refetch();
    }
  };

  return <Box>
    <Flex justify="space-between" align="center" mb={7} gap={4} wrap="wrap"><Box><Heading size="lg">{t('searchSites.title')}</Heading><Text color="text.muted" mt={1}>{t('searchSites.subtitle')}</Text></Box><GradientButton leftIcon={<IconPlus size={17} />} onClick={() => navigate('/search-sites/new')}>{t('searchSites.add')}</GradientButton></Flex>
    {query.isLoading && <Flex justify="center" py={16}><Spinner /></Flex>}
    {query.isError && <Alert status="error"><AlertIcon />{t('searchSites.loadError')}</Alert>}
    {query.data?.items.length === 0 && <Box bg="surface.raised" p={10} textAlign="center" borderRadius="2xl"><Text mb={4}>{t('searchSites.empty')}</Text><GradientButton leftIcon={<IconPlus size={17} />} onClick={() => navigate('/search-sites/new')}>{t('searchSites.add')}</GradientButton></Box>}
    <Stack spacing={3}>{query.data?.items.map((item) => <Box key={item.id} bg="surface.raised" p={5} borderRadius="2xl" boxShadow="sm"><Flex justify="space-between" gap={4} wrap="wrap"><Box><HStack><Heading size="sm">{item.name}</Heading>{item.is_in_use && <Badge colorScheme="purple">{t('searchSites.inUse')}</Badge>}</HStack><Text fontSize="sm" color="text.secondary" mt={2}>{item.site_key} · {item.base_url}</Text><Text fontSize="xs" color="text.muted" mt={1}>{item.has_pagination ? t('searchSites.paginationOn') : t('searchSites.paginationOff')} · {new Intl.DateTimeFormat(i18n.language).format(new Date(item.created_at))}</Text></Box><HStack><GradientButton size="sm" height={9} px={4} leftIcon={<IconPencil size={15} />} onClick={() => navigate(`/search-sites/${item.id}/edit?return_page=${page}&return_page_size=${pageSize}`)}>{t('searchSites.edit')}</GradientButton><Tooltip label={!item.can_delete ? t('searchSites.cannotDelete') : ''}><Button size="sm" variant="outline" sx={purpleOutline} leftIcon={<IconTrash size={15} />} isDisabled={!item.can_delete || remove.isPending} onClick={() => deleteItem(item.id, item.name)}>{t('searchSites.delete')}</Button></Tooltip></HStack></Flex></Box>)}</Stack>
    {(query.data?.total ?? 0) > 0 && <Flex mt={6} justify="space-between" align="center" gap={3}><HStack><Button size="sm" variant="outline" sx={purpleOutline} isDisabled={page <= 1} onClick={() => setPage(page - 1)}>{t('searchSites.previous')}</Button><Text fontSize="sm">{page} / {pages}</Text><Button size="sm" variant="outline" sx={purpleOutline} isDisabled={page >= pages} onClick={() => setPage(page + 1)}>{t('searchSites.next')}</Button></HStack><Select w="100px" size="sm" value={pageSize} onChange={(e) => setPage(1, Number(e.target.value))}><option value={10}>10</option><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></Select></Flex>}
  </Box>;
}
