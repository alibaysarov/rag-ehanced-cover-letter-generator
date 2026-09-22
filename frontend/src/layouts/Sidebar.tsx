import {
  Box,
  Divider,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerOverlay,
  Flex,
  Image,
  IconButton,
  VStack,
  useBreakpointValue,
  useColorMode,
  useDisclosure,
} from '@chakra-ui/react';
import {
  IconBriefcase,
  IconChartBar,
  IconMenu2,
  IconSearch,
  IconWorldSearch,
  IconSparkles,
  IconTemplate,
  IconX,
} from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { SidebarItem } from '@/components/ui/SidebarItem';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { UserCard } from '@/components/ui/UserCard';

function BrandMark() {
  const { colorMode } = useColorMode();
  const isDark = colorMode === 'dark';

  return (
    <Box position="relative" w="188px" h="30px">
      <Image
        src="/findjobforme-logo.svg"
        alt="FindJobFor.me"
        position="absolute"
        inset={0}
        w="188px"
        h="auto"
        opacity={isDark ? 0 : 1}
        transition="opacity 240ms ease"
      />
      <Image
        src="/findjobforme-logo-dark.svg"
        alt=""
        aria-hidden
        position="absolute"
        inset={0}
        w="188px"
        h="auto"
        opacity={isDark ? 1 : 0}
        transition="opacity 240ms ease"
      />
    </Box>
  );
}

interface SidebarContentProps {
  onNavigate?: () => void;
}

function SidebarContent({ onNavigate }: SidebarContentProps) {
  const { t } = useTranslation();

  const navItems = [
    { to: '/', end: true, icon: IconSparkles, label: t('nav.generate') },
    { to: '/auto-parse', icon: IconSearch, label: t('nav.autoParse') },
    { to: '/projects', icon: IconBriefcase, label: t('nav.projects') },
    { to: '/search-sites', icon: IconWorldSearch, label: t('nav.searchSites') },
    { to: '/letter-constructor/templates', icon: IconTemplate, label: t('nav.letterConstructor') },
    { to: '/stats', icon: IconChartBar, label: t('nav.stats') },
  ];

  return (
    <Flex direction="column" h="100%" w="100%">
      <Box px={6} py={6}>
        <BrandMark />
      </Box>
      <Box px={3} flex="1" overflowY="auto">
        <VStack spacing={1} align="stretch">
          {navItems.map((item) => (
            <SidebarItem
              key={item.to}
              to={item.to}
              end={'end' in item ? item.end : undefined}
              icon={item.icon}
              label={item.label}
              onNavigate={onNavigate}
            />
          ))}
        </VStack>
      </Box>
      <Divider borderColor="border.default" />
      <Box px={3} py={5}>
        <Flex justify="flex-end" mb={3}>
          <ThemeToggle />
        </Flex>
        <UserCard />
      </Box>
    </Flex>
  );
}

export function Sidebar() {
  const isDesktop = useBreakpointValue({ base: false, md: true }, { ssr: false });
  const { isOpen, onOpen, onClose } = useDisclosure();

  if (isDesktop) {
    return (
      <Box
        as="aside"
        position="sticky"
        top={0}
        h="100vh"
        w="260px"
        minW="260px"
        flexShrink={0}
        bg="surface.glass"
        borderRight="1px solid"
        borderColor="border.default"
        sx={{
          backdropFilter: 'blur(24px) saturate(160%)',
          WebkitBackdropFilter: 'blur(24px) saturate(160%)',
          '@supports not (backdrop-filter: blur(1px))': { background: 'surface.glass' },
        }}
        boxShadow="0 8px 32px rgba(32,55,72,0.06)"
      >
        <SidebarContent />
      </Box>
    );
  }

  return (
    <>
      <IconButton
        aria-label="Open navigation"
        icon={<IconMenu2 size={20} stroke={1.75} />}
        onClick={onOpen}
        position="fixed"
        top={4}
        left={4}
        zIndex={20}
        size="md"
        borderRadius="xl"
        bg="surface.glass"
        border="1px solid"
        borderColor="border.default"
        color="text.secondary"
        sx={{
          backdropFilter: 'blur(16px) saturate(160%)',
          WebkitBackdropFilter: 'blur(16px) saturate(160%)',
        }}
        _hover={{ bg: 'surface.glassStrong' }}
        boxShadow="0 4px 16px rgba(15,23,42,0.06)"
      />
      <Drawer isOpen={isOpen} placement="left" onClose={onClose} size="xs">
        <DrawerOverlay />
        <DrawerContent
          bg="surface.glass"
          sx={{
            backdropFilter: 'blur(24px) saturate(160%)',
            WebkitBackdropFilter: 'blur(24px) saturate(160%)',
          }}
        >
          <Flex justify="flex-end" px={4} pt={4}>
            <IconButton
              aria-label="Close navigation"
              icon={<IconX size={18} stroke={1.75} />}
              onClick={onClose}
              size="sm"
              variant="ghost"
              color="text.muted"
            />
          </Flex>
          <DrawerBody p={0}>
            <SidebarContent onNavigate={onClose} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </>
  );
}

export default Sidebar;
