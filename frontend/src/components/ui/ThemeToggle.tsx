import { IconButton, Tooltip, useColorMode } from '@chakra-ui/react';
import { IconMoonStars, IconSun } from '@tabler/icons-react';
import { useEffect } from 'react';

export function ThemeToggle() {
  const { colorMode, toggleColorMode } = useColorMode();
  const isDark = colorMode === 'dark';
  const label = isDark ? 'Включить светлую тему' : 'Включить тёмную тему';

  useEffect(() => {
    const favicon = document.querySelector<HTMLLinkElement>('#app-favicon');
    if (favicon) favicon.href = isDark ? '/favicon-dark.ico' : '/favicon.ico';
  }, [isDark]);

  return (
    <Tooltip label={label} hasArrow placement="top">
      <IconButton
        aria-label={label}
        icon={isDark ? <IconSun size={18} stroke={1.8} /> : <IconMoonStars size={18} stroke={1.8} />}
        onClick={toggleColorMode}
        size="sm"
        variant="glass"
        color="text.secondary"
        borderColor="border.default"
        _hover={{ bg: 'surface.glassStrong', color: 'brand.blue' }}
      />
    </Tooltip>
  );
}

export default ThemeToggle;
