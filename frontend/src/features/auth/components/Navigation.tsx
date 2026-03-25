import React from 'react';
import {
  Box,
  Flex,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
  useToast
} from '@chakra-ui/react';
import { IconChevronDown, IconUser } from '@tabler/icons-react';

import { useAuth } from '../hooks/useAuth';

const Navigation: React.FC = () => {
  const { user, logout, isLogoutLoading } = useAuth();
  const toast = useToast();

  const handleLogout = async () => {
    try {
      await logout();
      toast({
        title: 'Выход выполнен успешно',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <Box bg="white" borderBottom="1px" borderColor="gray.200" px={4} py={3}>
      <Flex justify="space-between" align="center" maxW="1200px" mx="auto">
        <Text fontSize="xl" fontWeight="bold" color="blue.600">
          Cover Letter Generator
        </Text>

        {user && (
          <Flex align="center" gap={4}>
            <Text color="gray.600">
              Добро пожаловать, {user.first_name} {user.last_name}
            </Text>

            <Menu>
              <MenuButton
                as={Button}
                variant="ghost"
                display="flex"
                alignItems="center"
                gap={2}
              >
                <IconUser size={20} />
                <IconChevronDown size={16} />
              </MenuButton>
              <MenuList>
                <MenuItem onClick={handleLogout} isDisabled={isLogoutLoading}>
                  {isLogoutLoading ? 'Выход...' : 'Выйти'}
                </MenuItem>
              </MenuList>
            </Menu>
          </Flex>
        )}
      </Flex>
    </Box>
  );
};

export default Navigation;
