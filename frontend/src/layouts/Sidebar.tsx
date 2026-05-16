import {
  Box,
  Divider,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerOverlay,
  Flex,
  IconButton,
  Text,
  VStack,
  useBreakpointValue,
  useDisclosure,
} from '@chakra-ui/react';
import {
  IconBriefcase,
  IconFile,
  IconMenu2,
  IconSparkles,
  IconUserCircle,
  IconX,
} from '@tabler/icons-react';
import { SidebarItem } from '@/components/ui/SidebarItem';
import { UserCard } from '@/components/ui/UserCard';

const NAV_ITEMS = [
  { to: '/', end: true, icon: IconSparkles, label: 'Generate' },
  { to: '/projects', icon: IconBriefcase, label: 'Projects' },
  { to: '/my-cvs', icon: IconFile, label: 'Resumes' },
  { to: '/profile', icon: IconUserCircle, label: 'Profile' },
] as const;

function BrandMark() {
  return (
    <Flex align="center" gap={3}>
      <Box
        w="28px"
        h="28px"
        borderRadius="10px"
        backgroundImage="accent.gradient"
        boxShadow="0 4px 12px rgba(99,102,241,0.35)"
      />
      <Text
        fontSize="xl"
        fontWeight={600}
        fontFamily="heading"
        color="slate.900"
        letterSpacing="-0.02em"
      >
        Coverly
      </Text>
    </Flex>
  );
}

interface SidebarContentProps {
  onNavigate?: () => void;
}

function SidebarContent({ onNavigate }: SidebarContentProps) {
  return (
    <Flex direction="column" h="100%" w="100%">
      <Box px={6} py={6}>
        <BrandMark />
      </Box>
      <Box px={3} flex="1" overflowY="auto">
        <VStack spacing={1} align="stretch">
          {NAV_ITEMS.map((item) => (
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
      <Divider borderColor="rgba(226,232,240,0.4)" />
      <Box px={3} py={5}>
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
        borderRight="1px solid rgba(255,255,255,0.6)"
        sx={{
          backdropFilter: 'blur(24px) saturate(160%)',
          WebkitBackdropFilter: 'blur(24px) saturate(160%)',
          '@supports not (backdrop-filter: blur(1px))': {
            background: 'rgba(255,255,255,0.85)',
          },
        }}
        boxShadow="inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 32px rgba(79,70,229,0.06)"
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
        border="1px solid rgba(255,255,255,0.6)"
        color="slate.700"
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
              color="slate.500"
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
