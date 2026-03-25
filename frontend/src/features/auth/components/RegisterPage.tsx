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
  useToast,
  Card,
  CardBody,
  Alert,
  AlertIcon,
  SimpleGrid,
} from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Validation schema
const registerSchema = z.object({
  first_name: z.string().min(2, 'Имя должно содержать минимум 2 символа'),
  last_name: z.string().min(2, 'Фамилия должна содержать минимум 2 символа'),
  email: z.string().email('Неверный email адрес'),
  password: z.string(),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Пароли не совпадают",
  path: ["confirmPassword"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { register: registerUser, isRegisterLoading, registerError, isAuthenticated } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: RegisterFormData) => {
    try {
      // Remove confirmPassword before sending to API
      const { confirmPassword, ...registerData } = data;
      await registerUser(registerData);
      toast({
        title: 'Регистрация выполнена успешно',
        description: 'Теперь вы можете войти в систему',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/login');
    } catch (error) {
      // Error is handled by the useAuth hook
      console.error('Register error:', error);
    }
  };

  return (
    <Container maxW="md" py={12}>
      <Card>
        <CardBody>
          <Stack spacing={8}>
            <Box textAlign="center">
              <Heading size="lg" mb={2}>
                Создание аккаунта
              </Heading>
              <Text color="gray.600">
                Заполните форму для регистрации
              </Text>
            </Box>

            <form onSubmit={handleSubmit(onSubmit)}>
              <Stack spacing={6}>
                {registerError && (
                  <Alert status="error">
                    <AlertIcon />
                    {registerError}
                  </Alert>
                )}

                <SimpleGrid columns={2} spacing={4}>
                  <FormControl isInvalid={!!errors.first_name}>
                    <FormLabel>Имя</FormLabel>
                    <Input
                      placeholder="Иван"
                      {...register('first_name')}
                    />
                    <FormErrorMessage>
                      {errors.first_name?.message}
                    </FormErrorMessage>
                  </FormControl>

                  <FormControl isInvalid={!!errors.last_name}>
                    <FormLabel>Фамилия</FormLabel>
                    <Input
                      placeholder="Иванов"
                      {...register('last_name')}
                    />
                    <FormErrorMessage>
                      {errors.last_name?.message}
                    </FormErrorMessage>
                  </FormControl>
                </SimpleGrid>

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
                    placeholder="Минимум 6 символов"
                    {...register('password')}
                  />
                  <FormErrorMessage>
                    {errors.password?.message}
                  </FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.confirmPassword}>
                  <FormLabel>Подтверждение пароля</FormLabel>
                  <Input
                    type="password"
                    placeholder="Повторите пароль"
                    {...register('confirmPassword')}
                  />
                  <FormErrorMessage>
                    {errors.confirmPassword?.message}
                  </FormErrorMessage>
                </FormControl>

                <Button
                  type="submit"
                  colorScheme="blue"
                  size="lg"
                  width="full"
                  isLoading={isSubmitting || isRegisterLoading}
                  loadingText="Создание аккаунта..."
                >
                  Зарегистрироваться
                </Button>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text>
                Уже есть аккаунт?{' '}
                <Link as={RouterLink} to="/login" color="blue.500">
                  Войти
                </Link>
              </Text>
            </Box>
          </Stack>
        </CardBody>
      </Card>
    </Container>
  );
};

export default RegisterPage;
