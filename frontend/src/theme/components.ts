import type { ComponentStyleConfig, ThemeOverride } from '@chakra-ui/react';

const Button: ComponentStyleConfig = {
  baseStyle: {
    fontFamily: 'body',
    fontWeight: 600,
    borderRadius: 'xl',
  },
  variants: {
    solid: {
      color: 'white',
      backgroundImage: 'accent.gradient',
      backgroundSize: '200% 200%',
      backgroundPosition: '0% 0%',
      boxShadow: '0 4px 16px rgba(99, 102, 241, 0.35)',
      transition:
        'background-position 400ms ease, box-shadow 200ms ease, transform 200ms ease',
      _hover: {
        backgroundPosition: '100% 100%',
        boxShadow: '0 6px 24px rgba(99, 102, 241, 0.45)',
        _disabled: {
          backgroundPosition: '0% 0%',
        },
      },
      _active: {
        backgroundPosition: '100% 100%',
      },
    },
    glass: {
      bg: 'surface.glass',
      color: 'slate.900',
      backdropFilter: 'blur(16px) saturate(160%)',
      border: '1px solid rgba(255, 255, 255, 0.6)',
      _hover: {
        bg: 'surface.glassStrong',
      },
    },
    ghost: {
      bg: 'transparent',
      color: 'slate.700',
      _hover: {
        bg: 'surface.glassStrong',
      },
    },
    link: {
      color: 'aurora.indigo',
      _hover: {
        textDecoration: 'none',
        backgroundImage: 'accent.gradient',
        backgroundClip: 'text',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        color: 'transparent',
      },
    },
  },
};

const inputFieldStyles = {
  bg: 'rgba(255, 255, 255, 0.6)',
  border: '1px solid',
  borderColor: 'rgba(226, 232, 240, 0.6)',
  _hover: {
    borderColor: 'rgba(99, 102, 241, 0.4)',
  },
  _focus: {
    borderColor: 'aurora.indigo',
    boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.18)',
  },
  _focusVisible: {
    borderColor: 'aurora.indigo',
    boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.18)',
  },
};

const Input: ComponentStyleConfig = {
  variants: {
    outline: {
      field: inputFieldStyles,
    },
  },
  defaultProps: {
    variant: 'outline',
  },
};

const Textarea: ComponentStyleConfig = {
  variants: {
    outline: inputFieldStyles,
  },
  defaultProps: {
    variant: 'outline',
  },
};

const Select: ComponentStyleConfig = {
  variants: {
    outline: {
      field: inputFieldStyles,
    },
  },
  defaultProps: {
    variant: 'outline',
  },
};

const Card: ComponentStyleConfig = {
  baseStyle: {
    container: {
      bg: 'surface.glass',
      backdropFilter: 'blur(24px) saturate(160%)',
      border: '1px solid rgba(255, 255, 255, 0.6)',
      borderRadius: '3xl',
      boxShadow:
        'inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 32px rgba(79,70,229,0.08), 0 2px 8px rgba(15,23,42,0.04)',
    },
  },
};

const Modal: ComponentStyleConfig = {
  baseStyle: {
    overlay: {
      bg: 'blackAlpha.300',
      backdropFilter: 'blur(8px)',
    },
    dialog: {
      bg: 'surface.glass',
      backdropFilter: 'blur(24px) saturate(160%)',
      border: '1px solid rgba(255, 255, 255, 0.6)',
      borderRadius: '3xl',
      boxShadow:
        'inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 32px rgba(79,70,229,0.08), 0 2px 8px rgba(15,23,42,0.04)',
    },
  },
};

const Drawer: ComponentStyleConfig = {
  baseStyle: {
    overlay: {
      bg: 'blackAlpha.300',
      backdropFilter: 'blur(8px)',
    },
    dialog: {
      bg: 'surface.glass',
      backdropFilter: 'blur(24px) saturate(160%)',
      border: '1px solid rgba(255, 255, 255, 0.6)',
    },
  },
};

export const components: ThemeOverride['components'] = {
  Button,
  Input,
  Textarea,
  Select,
  Card,
  Modal,
  Drawer,
};
