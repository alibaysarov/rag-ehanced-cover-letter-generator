import { Button } from '@chakra-ui/react';
import type { ButtonProps } from '@chakra-ui/react';
import { forwardRef } from 'react';

const ACCENT_GRADIENT =
  'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)';

export interface GradientButtonProps extends Omit<ButtonProps, 'variant'> {
  variant?: 'solid' | 'outline' | 'ghost';
}

const COMMON: ButtonProps = {
  variant: 'unstyled',
  borderRadius: 'xl',
  fontFamily: 'body',
  fontWeight: 600,
  px: 6,
  py: 0,
  height: 10,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const solidSx = {
  color: 'white',
  backgroundImage: ACCENT_GRADIENT,
  backgroundSize: '200% 200%',
  backgroundPosition: '0% 0%',
  boxShadow: '0 4px 16px rgba(99, 102, 241, 0.35)',
  transition:
    'background-position 400ms ease, box-shadow 200ms ease, transform 200ms ease',
  _hover: {
    backgroundPosition: '100% 100%',
    boxShadow: '0 6px 24px rgba(99, 102, 241, 0.45)',
    _disabled: { backgroundPosition: '0% 0%' },
  },
  _active: { backgroundPosition: '100% 100%' },
};

// Outline: gradient border via ::before mask trick + gradient text directly.
const outlineSx = {
  position: 'relative' as const,
  background: 'transparent',
  backgroundImage: ACCENT_GRADIENT,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  color: 'transparent',
  transition: 'transform 200ms ease',
  _before: {
    content: '""',
    position: 'absolute',
    inset: 0,
    borderRadius: 'inherit',
    padding: '1.5px',
    background: ACCENT_GRADIENT,
    WebkitMask:
      'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
    WebkitMaskComposite: 'xor',
    maskComposite: 'exclude',
    pointerEvents: 'none',
  },
};

const ghostSx = {
  background: 'transparent',
  color: 'slate.700',
  transition: 'color 200ms ease',
  _hover: {
    backgroundImage: ACCENT_GRADIENT,
    WebkitBackgroundClip: 'text',
    backgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    color: 'transparent',
  },
};

export const GradientButton = forwardRef<HTMLButtonElement, GradientButtonProps>(
  ({ variant = 'solid', sx, ...rest }, ref) => {
    const variantSx =
      variant === 'solid' ? solidSx : variant === 'outline' ? outlineSx : ghostSx;

    return (
      <Button
        ref={ref}
        {...COMMON}
        sx={{ ...variantSx, ...sx }}
        {...rest}
      />
    );
  },
);

GradientButton.displayName = 'GradientButton';
