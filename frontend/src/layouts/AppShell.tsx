import { Box, Container, Flex } from '@chakra-ui/react';
import type { ReactNode } from 'react';
import { AuroraBackground } from '@/components/ui/AuroraBackground';
import { Sidebar } from '@/layouts/Sidebar';
import { PageTransition } from '@/layouts/PageTransition';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <Box position="relative" minH="100vh">
      <AuroraBackground />
      <Flex minH="100vh" align="stretch">
        <Sidebar />
        <Box as="main" flex="1" minW={0} overflowX="hidden">
          <Container maxW="1120px" px={{ base: 6, md: 12 }} py={10}>
            <PageTransition>{children}</PageTransition>
          </Container>
        </Box>
      </Flex>
    </Box>
  );
}

export default AppShell;
