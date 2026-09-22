import { Box } from '@chakra-ui/react';

const MESH_BACKGROUND = [
  'radial-gradient(at 12% 8%, rgba(0,123,255,0.13) 0px, transparent 44%)',
  'radial-gradient(at 92% 18%, rgba(32,55,72,0.10) 0px, transparent 42%)',
  '#F8FAFC',
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
