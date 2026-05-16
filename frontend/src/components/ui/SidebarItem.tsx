import { Box, Flex, Text } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { ComponentType, ReactNode } from 'react';

interface SidebarItemProps {
  to: string;
  end?: boolean;
  icon: ComponentType<{ size?: number | string; stroke?: number; color?: string }>;
  label: string;
  onNavigate?: () => void;
}

const EASING: [number, number, number, number] = [0.4, 0, 0.2, 1];

export function SidebarItem({
  to,
  end,
  icon: Icon,
  label,
  onNavigate,
}: SidebarItemProps): ReactNode {
  return (
    <NavLink to={to} end={end} onClick={onNavigate} style={{ textDecoration: 'none' }}>
      {({ isActive }) => (
        <Flex
          position="relative"
          align="center"
          gap={3}
          px={3}
          py={2.5}
          borderRadius="xl"
          bg={isActive ? 'surface.glassStrong' : 'transparent'}
          color={isActive ? 'slate.900' : 'slate.700'}
          transition="background-color 180ms ease, color 180ms ease"
          _hover={{ bg: 'surface.glassStrong' }}
          role="group"
        >
          <motion.span
            aria-hidden
            initial={false}
            animate={{ scaleY: isActive ? 1 : 0, opacity: isActive ? 1 : 0 }}
            transition={{ duration: 0.22, ease: EASING }}
            style={{
              position: 'absolute',
              left: 0,
              top: 6,
              bottom: 6,
              width: 3,
              borderRadius: 999,
              background:
                'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
              transformOrigin: 'center',
              pointerEvents: 'none',
            }}
          />
          <Box
            display="inline-flex"
            alignItems="center"
            color={isActive ? 'aurora.indigo' : 'currentColor'}
            transition="color 180ms ease"
          >
            <Icon size={20} stroke={1.75} />
          </Box>
          <Text fontSize="sm" fontWeight={isActive ? 600 : 500} fontFamily="body">
            {label}
          </Text>
        </Flex>
      )}
    </NavLink>
  );
}

export default SidebarItem;
