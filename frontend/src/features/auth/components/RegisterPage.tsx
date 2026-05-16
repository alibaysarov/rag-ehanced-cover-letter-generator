import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  Flex,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  Input,
  Stack,
  Text,
  Link,
  useToast,
  SimpleGrid,
} from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { AuroraBackground } from '@/components/ui/AuroraBackground';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';

const registerSchema = z
  .object({
    first_name: z.string().min(2, 'Имя должно содержать минимум 2 символа'),
    last_name: z.string().min(2, 'Фамилия должна содержать минимум 2 символа'),
    email: z.string().email('Неверный email адрес'),
    password: z.string().min(8, 'Минимум 8 символов'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Пароли не совпадают',
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { register: registerUser, isRegisterLoading, isAuthenticated } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const { confirmPassword: _confirm, ...registerData } = data;
      await registerUser(registerData);
      toast({
        title: 'Аккаунт создан',
        description: 'Теперь можно войти',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/login');
    } catch (error) {
      toast({
        title: 'Ошибка регистрации',
        description: error instanceof Error ? error.message : 'Попробуйте ещё раз',
        status: 'error',
        duration: 3500,
        isClosable: true,
      });
    }
  };

  return (
    <Box position="relative" minH="100vh">
      <AuroraBackground />
      <Flex minH="100vh" align="center" justify="center" px={{ base: 6, md: 8 }} py={12}>
        <GlassCard padding={{ base: 8, md: 10 }} radius="3xl" maxW="480px" w="full">
          <Stack spacing={8}>
            <Box>
              <Heading
                fontFamily="heading"
                fontSize="3xl"
                fontWeight={600}
                color="slate.900"
                letterSpacing="-0.02em"
                mb={2}
              >
                Создайте аккаунт
              </Heading>
              <Text color="slate.500" fontSize="sm">
                Заполните форму, чтобы начать пользоваться Coverly
              </Text>
            </Box>

            <form onSubmit={handleSubmit(onSubmit)}>
              <Stack spacing={5}>
                <SimpleGrid columns={2} spacing={4}>
                  <FormControl isInvalid={!!errors.first_name}>
                    <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                      Имя
                    </FormLabel>
                    <Input placeholder="Иван" {...register('first_name')} />
                    <FormErrorMessage>{errors.first_name?.message}</FormErrorMessage>
                  </FormControl>

                  <FormControl isInvalid={!!errors.last_name}>
                    <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                      Фамилия
                    </FormLabel>
                    <Input placeholder="Иванов" {...register('last_name')} />
                    <FormErrorMessage>{errors.last_name?.message}</FormErrorMessage>
                  </FormControl>
                </SimpleGrid>

                <FormControl isInvalid={!!errors.email}>
                  <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                    Email
                  </FormLabel>
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    autoComplete="email"
                    {...register('email')}
                  />
                  <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.password}>
                  <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                    Пароль
                  </FormLabel>
                  <Input
                    type="password"
                    placeholder="Минимум 8 символов"
                    autoComplete="new-password"
                    {...register('password')}
                  />
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.confirmPassword}>
                  <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                    Подтверждение пароля
                  </FormLabel>
                  <Input
                    type="password"
                    placeholder="Повторите пароль"
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                  />
                  <FormErrorMessage>{errors.confirmPassword?.message}</FormErrorMessage>
                </FormControl>

                <GradientButton
                  type="submit"
                  size="lg"
                  w="full"
                  isLoading={isSubmitting || isRegisterLoading}
                  loadingText="Создаём аккаунт..."
                  mt={2}
                >
                  Зарегистрироваться
                </GradientButton>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text fontSize="sm" color="slate.500">
                Уже есть аккаунт?{' '}
                <Link
                  as={RouterLink}
                  to="/login"
                  fontWeight={600}
                  sx={{
                    backgroundImage:
                      'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    color: 'transparent',
                  }}
                >
                  Войти
                </Link>
              </Text>
            </Box>
          </Stack>
        </GlassCard>
      </Flex>
    </Box>
  );
};

export default RegisterPage;
