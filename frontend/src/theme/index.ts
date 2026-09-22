import { extendTheme } from '@chakra-ui/react';
import { colors } from './colors';
import { fonts } from './fonts';
import { components } from './components';

export const theme = extendTheme({
  config: { initialColorMode: 'light', useSystemColorMode: false },
  colors,
  fonts,
  styles: {
    global: {
      'html, body': {
        bg: 'transparent',
        color: 'slate.900',
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
    },
  },
  components,
});
