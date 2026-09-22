import { extendTheme } from '@chakra-ui/react';
import { components } from './components';

/**
 * The single source of truth for the product design system.
 * Chakra props such as `p={6}`, `fontSize="sm"` and responsive `{ base, md }`
 * all resolve through these scales.
 */
export const designTokens = {
  breakpoints: {
    sm: '30em',
    md: '48em',
    lg: '62em',
    xl: '80em',
    '2xl': '96em',
  },
  fonts: {
    heading: "'Inter Variable', 'Inter', system-ui, sans-serif",
    body: "'Inter Variable', 'Inter', system-ui, sans-serif",
    mono: "'JetBrains Mono', ui-monospace, monospace",
  },
  fontSizes: {
    xs: '0.75rem',
    sm: '0.875rem',
    md: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },
  fontWeights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    mediumBold: 650,
    bold: 700,
    extraBold: 800,
  },
  lineHeights: {
    normal: 'normal',
    short: 1.25,
    base: 1.5,
    relaxed: 1.65,
    tall: 1.75,
  },
  space: {
    0: '0',
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    7: '1.75rem',
    8: '2rem',
    10: '2.5rem',
    12: '3rem',
    14: '3.5rem',
    16: '4rem',
    pageX: '3rem',
    pageY: '2.5rem',
    section: '2rem',
    control: '0.75rem',
  },
  sizes: {
    sidebar: '16.25rem',
    content: '70rem',
    control: '2.5rem',
    touchTarget: '2.75rem',
    brandMark: '11.75rem',
    brandMarkHeight: '1.875rem',
    form: '56.25rem',
    editorLibrary: '18.75rem',
    graphNode: '18.75rem',
  },
  radii: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.25rem',
    '3xl': '1.5rem',
    full: '9999px',
  },
  shadows: {
    card: '0 8px 28px rgba(32, 55, 72, 0.08), 0 2px 8px rgba(32, 55, 72, 0.04)',
    dialog: '0 8px 28px rgba(32, 55, 72, 0.12), 0 2px 8px rgba(32, 55, 72, 0.05)',
    focus: '0 0 0 3px rgba(0, 123, 255, 0.30)',
    focusSubtle: '0 0 0 3px rgba(0, 123, 255, 0.18)',
    primary: '0 4px 16px rgba(0, 123, 255, 0.28)',
    primaryHover: '0 6px 24px rgba(0, 123, 255, 0.36)',
    danger: '0 4px 16px rgba(225, 29, 72, 0.28)',
    dangerHover: '0 6px 20px rgba(225, 29, 72, 0.36)',
  },
  transitions: {
    colors: 'background-color 180ms ease, border-color 180ms ease, color 180ms ease, box-shadow 180ms ease',
    theme: 'background-color 240ms ease, color 240ms ease',
    interactive: 'transform 180ms ease, box-shadow 180ms ease',
  },
  colors: {
    brand: { navy: '#1A202C', blue: '#007BFF', steel: '#203748', cloud: '#F8FAFC' },
    slate: { 50: '#F8FAFC', 100: '#F1F5F9', 200: '#E2E8F0', 300: '#CBD5E1', 400: '#94A3B8', 500: '#64748B', 600: '#475569', 700: '#203748', 800: '#1A202C', 900: '#1A202C' },
    blue: { 50: '#EAF4FF', 100: '#D6EAFF', 200: '#ADD5FF', 300: '#84C0FF', 400: '#3D9BFF', 500: '#007BFF', 600: '#0069D9', 700: '#0056B3', 800: '#00458F', 900: '#00366F' },
    purple: { 50: '#EAF4FF', 100: '#D6EAFF', 200: '#ADD5FF', 300: '#84C0FF', 400: '#3D9BFF', 500: '#007BFF', 600: '#0069D9', 700: '#0056B3', 800: '#00458F', 900: '#00366F' },
    aurora: { indigo: '#007BFF' },
    accent: { gradient: 'linear-gradient(135deg, #007BFF 0%, #0056B3 100%)' },
    danger: { 50: '#FFF1F2', 100: '#FFE4E6', 500: '#E11D48', 600: '#BE123C', 700: '#9F1239' },
    success: { 500: '#10B981' },
  },
} as const;

export const theme = extendTheme({
  config: { initialColorMode: 'light', useSystemColorMode: false },
  breakpoints: designTokens.breakpoints,
  colors: designTokens.colors,
  fonts: designTokens.fonts,
  fontSizes: designTokens.fontSizes,
  fontWeights: designTokens.fontWeights,
  lineHeights: designTokens.lineHeights,
  space: designTokens.space,
  sizes: designTokens.sizes,
  radii: designTokens.radii,
  shadows: designTokens.shadows,
  semanticTokens: {
    colors: {
      'surface.canvas': { default: 'brand.cloud', _dark: '#101820' },
      'surface.raised': { default: '#FFFFFF', _dark: '#1A202C' },
      'surface.glass': { default: 'rgba(248, 250, 252, 0.88)', _dark: 'rgba(26, 32, 44, 0.88)' },
      'surface.glassStrong': { default: '#FFFFFF', _dark: '#203748' },
      'text.primary': { default: 'brand.navy', _dark: 'brand.cloud' },
      'text.secondary': { default: 'slate.600', _dark: '#C5D1DA' },
      'text.muted': { default: 'slate.500', _dark: '#9FB0BD' },
      'border.default': { default: 'rgba(32, 55, 72, 0.12)', _dark: 'rgba(248, 250, 252, 0.16)' },
      'border.subtle': { default: 'slate.200', _dark: 'rgba(248, 250, 252, 0.10)' },
    },
  },
  styles: {
    global: {
      'html, body': {
        bg: 'surface.canvas',
        color: 'text.primary',
        transition: designTokens.transitions.theme,
      },
      body: {
        fontFamily: 'body',
        fontSize: 'md',
        lineHeight: 'base',
      },
      'h1, h2, h3, h4': {
        fontFamily: 'heading',
        letterSpacing: '-0.02em',
        lineHeight: 'short',
      },
      '*:focus-visible': {
        outline: 'none',
        boxShadow: 'focus',
        borderRadius: 'md',
      },
      '*, *::before, *::after': {
        transition: designTokens.transitions.colors,
      },
    },
  },
  components,
});
