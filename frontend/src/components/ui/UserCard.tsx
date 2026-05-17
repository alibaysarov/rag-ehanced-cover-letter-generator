import {
  Box,
  Flex,
  IconButton,
  Text,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { IconLogout } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth';

function getInitials(firstName?: string | null, lastName?: string | null, email?: string): string {
  const f = (firstName ?? '').trim();
  const l = (lastName ?? '').trim();
  if (f || l) {
    return `${f.charAt(0)}${l.charAt(0)}`.toUpperCase() || '?';
  }
  if (email) return email.charAt(0).toUpperCase();
  return '?';
}

function getDisplayName(firstName?: string | null, lastName?: string | null, email?: string): string {
  const f = (firstName ?? '').trim();
  const l = (lastName ?? '').trim();
  const name = `${f} ${l}`.trim();
  return name || email || 'User';
}

export function UserCard() {
  const { user, logout, isLogoutLoading } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  if (!user) return null;

  const initials = getInitials(user.first_name, user.last_name, user.email);
  const displayName = getDisplayName(user.first_name, user.last_name, user.email);

  const handleLogout = async () => {
    try {
      await logout();
      toast({
        title: 'Logged out',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Logout failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const goToProfile = () => navigate('/profile');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      goToProfile();
    }
  };

  return (
    <Flex
      align="center"
      gap={3}
      px={3}
      py={2.5}
      borderRadius="2xl"
      bg="surface.glass"
      border="1px solid rgba(255,255,255,0.6)"
      cursor="pointer"
      role="button"
      tabIndex={0}
      aria-label="Открыть профиль"
      onClick={goToProfile}
      onKeyDown={handleKeyDown}
      transition="background 0.15s ease"
      _hover={{ bg: 'surface.glassStrong' }}
      _focusVisible={{
        outline: '2px solid',
        outlineColor: 'accent.500',
        outlineOffset: '2px',
      }}
    >
      <Flex
        align="center"
        justify="center"
        w="38px"
        h="38px"
        minW="38px"
        borderRadius="full"
        backgroundImage="accent.gradient"
        color="white"
        fontWeight={600}
        fontSize="sm"
        fontFamily="heading"
        boxShadow="0 4px 12px rgba(99,102,241,0.35)"
      >
        {initials}
      </Flex>
      <Box flex="1" minW={0}>
        <Text
          fontSize="sm"
          fontWeight={600}
          color="slate.900"
          isTruncated
          fontFamily="body"
        >
          {displayName}
        </Text>
        <Text fontSize="xs" color="slate.500" isTruncated fontFamily="body">
          {user.email}
        </Text>
      </Box>
      <Tooltip label="Sign out" hasArrow placement="top">
        <IconButton
          aria-label="Sign out"
          icon={<IconLogout size={18} stroke={1.75} />}
          size="sm"
          variant="ghost"
          isLoading={isLogoutLoading}
          onClick={(e) => {
            e.stopPropagation();
            handleLogout();
          }}
          onKeyDown={(e) => e.stopPropagation()}
          color="slate.500"
          _hover={{ color: 'danger.500', bg: 'surface.glassStrong' }}
        />
      </Tooltip>
    </Flex>
  );
}

export default UserCard;
