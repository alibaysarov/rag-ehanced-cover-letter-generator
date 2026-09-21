import { Button, HStack } from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function ConstructorTabs() {
  const location = useLocation(); const navigate = useNavigate();
  const { t } = useTranslation();
  return <HStack mb={6}>
    <Button colorScheme={location.pathname.includes('/templates') ? 'purple' : 'gray'} onClick={() => navigate('/letter-constructor/templates')}>{t('letterConstructor.tabs.templates')}</Button>
    <Button colorScheme={location.pathname.includes('/phrases') ? 'purple' : 'gray'} onClick={() => navigate('/letter-constructor/phrases')}>{t('letterConstructor.tabs.phrases')}</Button>
  </HStack>;
}
