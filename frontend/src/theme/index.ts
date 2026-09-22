import { extendTheme } from '@chakra-ui/react';
import { colors } from './colors';
import { fonts } from './fonts';
import { components } from './components';

export const theme = extendTheme({
  config: { initialColorMode: 'light', useSystemColorMode: false },
  colors,
  fonts,
  semanticTokens: {
    colors: {
      'surface.canvas': { default: 'brand.cloud', _dark: '#101820' },
      'surface.raised': { default: '#FFFFFF', _dark: '#1A202C' },
      'surface.glass': { default: 'rgba(248, 250, 252, 0.88)', _dark: 'rgba(26, 32, 44, 0.88)' },
      'surface.glassStrong': { default: '#FFFFFF', _dark: '#203748' },
      'text.primary': { default: 'brand.navy', _dark: 'brand.cloud' },
      'text.secondary': { default: 'text.secondary', _dark: '#C5D1DA' },
      'text.muted': { default: 'text.muted', _dark: '#9FB0BD' },
      'border.default': { default: 'rgba(32, 55, 72, 0.12)', _dark: 'rgba(248, 250, 252, 0.16)' },
      'border.subtle': { default: 'slate.200', _dark: 'rgba(248, 250, 252, 0.10)' },
    },
  },
  styles: {
    global: {
      'html, body': {
        bg: 'surface.canvas',
        color: 'text.primary',
        transition: 'background-color 240ms ease, color 240ms ease',
      },
      body: {
        fontFamily: 'body',
      },
      'h1, h2, h3, h4': {
        fontFamily: 'heading',
        letterSpacing: '-0.02em',
      },
      '*:focus-visible': {
        outline: 'none',
        boxShadow: '0 0 0 3px rgba(0, 123, 255, 0.30)',
        borderRadius: '8px',
      },
      '*, *::before, *::after': {
        transitionProperty: 'background-color, border-color, color, box-shadow',
        transitionDuration: '180ms',
        transitionTimingFunction: 'ease',
      },
    },
  },
  components,
});
