import { Box } from '@chakra-ui/react';
import type { BoxProps } from '@chakra-ui/react';
import { forwardRef } from 'react';

export interface GlassCardProps extends BoxProps {
  hover?: boolean;
  radius?: '2xl' | '3xl';
}

const BASE_SHADOW =
  'inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 32px rgba(79,70,229,0.08), 0 2px 8px rgba(15,23,42,0.04)';

const HOVER_SHADOW =
  'inset 0 1px 0 rgba(255,255,255,0.6), 0 14px 40px rgba(79,70,229,0.14), 0 4px 12px rgba(15,23,42,0.06)';

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ hover = false, radius = '3xl', padding, children, sx, ...rest }, ref) => {
    const borderRadiusPx = radius === '3xl' ? '24px' : '20px';

    return (
      <Box
        ref={ref}
        padding={padding}
        bg="surface.glass"
        border="1px solid rgba(255, 255, 255, 0.6)"
        borderRadius={borderRadiusPx}
        boxShadow={BASE_SHADOW}
        transition="transform 200ms ease, box-shadow 200ms ease"
        _hover={
          hover
            ? { transform: 'translateY(-2px)', boxShadow: HOVER_SHADOW }
            : undefined
        }
        sx={{
          backdropFilter: 'blur(24px) saturate(160%)',
          WebkitBackdropFilter: 'blur(24px) saturate(160%)',
          '@supports not (backdrop-filter: blur(1px))': {
            background: 'rgba(255, 255, 255, 0.85)',
          },
          ...sx,
        }}
        {...rest}
      >
        {children}
      </Box>
    );
  },
);

GlassCard.displayName = 'GlassCard';
