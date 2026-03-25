import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  Button,
  Container,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  Input,
  Stack,
  Text,
  Link,
  Card,
  CardBody,
  Alert,
  AlertIcon,
  useToast
} from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Validation schema
const loginSchema = z.object({
  email: z.string().email('Неверный email адрес'),
  password: z.string(),
});

type LoginFormData = z.infer<typeof loginSchema>;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { login, isLoginLoading, isAuthenticated } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Redirect if already authenticated
  useEffect(() => {
    
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data);
      toast({
        title: 'Вход выполнен успешно',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/');
    } catch (error) {
      // Error is handled by the useAuth hook
      toast({
        title: 'Ошибка при входе',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      console.error('Login error:', error);
    }
  };

  return (
    <Container maxW="md" py={12}>
      <Card>
        <CardBody>
          <Stack spacing={8}>
            <Box textAlign="center">
              <Heading size="lg" mb={2}>
                Вход в аккаунт
              </Heading>
              <Text color="gray.600">
                Введите свои данные для входа
              </Text>
            </Box>

            <form onSubmit={handleSubmit(onSubmit)}>
              <Stack spacing={6}>
                <FormControl isInvalid={!!errors.email}>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    {...register('email')}
                  />
                  <FormErrorMessage>
                    {errors.email?.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.password}>
                  <FormLabel>Пароль</FormLabel>
                  <Input
                    type="password"
                    placeholder="Ваш пароль"
                    {...register('password')}
                  />
                  <FormErrorMessage>
                    {errors.password?.message}
                  </FormErrorMessage>
                </FormControl>

                <Button
                  type="submit"
                  colorScheme="blue"
                  size="lg"
                  width="full"
                  isLoading={isSubmitting || isLoginLoading}
                  loadingText="Выполняется вход..."
                >
                  Войти
                </Button>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text>
                Нет аккаунта?{' '}
                <Link as={RouterLink} to={'/register'} color="blue.500">
                  Зарегистрироваться
                </Link>
              </Text>
            </Box>
          </Stack>
        </CardBody>
      </Card>
    </Container>
  );
};

export default LoginPage;
