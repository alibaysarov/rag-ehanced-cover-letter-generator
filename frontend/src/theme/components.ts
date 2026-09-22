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
      bg: 'brand.blue',
      backgroundImage: 'accent.gradient',
      backgroundSize: '200% 200%',
      backgroundPosition: '0% 0%',
      boxShadow: 'primary',
      transition:
        'background-position 400ms ease, box-shadow 200ms ease, transform 200ms ease',
      _hover: {
        backgroundPosition: '100% 100%',
        boxShadow: 'primaryHover',
        _disabled: {
          backgroundPosition: '0% 0%',
        },
      },
      _active: {
        backgroundPosition: '100% 100%',
      },
      _disabled: {
        bg: 'blue.700',
        backgroundImage: 'none',
        color: 'white',
        opacity: 0.58,
        boxShadow: 'none',
        cursor: 'not-allowed',
      },
    },
    danger: {
      color: 'white',
      bg: 'danger.500',
      boxShadow: 'danger',
      transition: 'background-color 180ms ease, box-shadow 180ms ease, transform 180ms ease',
      _hover: {
        bg: 'danger.600',
        boxShadow: 'dangerHover',
        _disabled: { bg: 'danger.700', boxShadow: 'none' },
      },
      _active: { bg: 'danger.700', transform: 'translateY(1px)' },
      _disabled: {
        bg: 'danger.700',
        color: 'white',
        opacity: 0.58,
        boxShadow: 'none',
        cursor: 'not-allowed',
      },
    },
    glass: {
      bg: 'surface.glass',
      color: 'text.primary',
      backdropFilter: 'blur(16px) saturate(160%)',
      border: '1px solid',
      borderColor: 'border.default',
      _hover: {
        bg: 'surface.glassStrong',
      },
    },
    ghost: {
      bg: 'transparent',
      color: 'text.secondary',
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
  bg: 'surface.raised',
  border: '1px solid',
  borderColor: 'border.default',
  color: 'text.primary',
  _placeholder: { color: 'text.muted' },
  _hover: {
    borderColor: 'blue.400',
  },
  _focus: {
    borderColor: 'aurora.indigo',
    boxShadow: 'focusSubtle',
  },
  _focusVisible: {
    borderColor: 'aurora.indigo',
    boxShadow: 'focusSubtle',
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
      border: '1px solid',
      borderColor: 'border.default',
      borderRadius: '3xl',
      boxShadow: 'card',
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
      border: '1px solid',
      borderColor: 'border.default',
      borderRadius: '3xl',
      boxShadow: 'dialog',
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
      border: '1px solid',
      borderColor: 'border.default',
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
