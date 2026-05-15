import { Box } from '@chakra-ui/react';

const MESH_BACKGROUND = [
  'radial-gradient(at 18% 12%, rgba(99,102,241,0.22) 0px, transparent 50%)',
  'radial-gradient(at 82% 28%, rgba(217,70,239,0.18) 0px, transparent 55%)',
  'radial-gradient(at 50% 92%, rgba(6,182,212,0.20) 0px, transparent 55%)',
  '#FAFAFB',
].join(', ');

const NOISE_DATA_URI =
  "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='matrix' values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")";

export function AuroraBackground() {
  return (
    <Box
      aria-hidden
      position="fixed"
      inset={0}
      zIndex={-1}
      pointerEvents="none"
      background={MESH_BACKGROUND}
    >
      <Box
        position="absolute"
        inset={0}
        opacity={0.02}
        backgroundImage={NOISE_DATA_URI}
        backgroundRepeat="repeat"
      />
    </Box>
  );
}
