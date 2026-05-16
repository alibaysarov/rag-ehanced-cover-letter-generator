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
} from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { AuroraBackground } from '@/components/ui/AuroraBackground';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';

const loginSchema = z.object({
  email: z.string().email('Неверный email адрес'),
  password: z.string().min(1, 'Введите пароль'),
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

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data);
      toast({
        title: 'Вход выполнен',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
      navigate('/');
    } catch (error) {
      toast({
        title: 'Ошибка при входе',
        description: error instanceof Error ? error.message : 'Проверьте email и пароль',
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
        <GlassCard padding={{ base: 8, md: 10 }} radius="3xl" maxW="440px" w="full">
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
                С возвращением
              </Heading>
              <Text color="slate.500" fontSize="sm">
                Войдите в свой аккаунт Coverly
              </Text>
            </Box>

            <form onSubmit={handleSubmit(onSubmit)}>
              <Stack spacing={5}>
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
                    placeholder="••••••••"
                    autoComplete="current-password"
                    {...register('password')}
                  />
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

                <GradientButton
                  type="submit"
                  size="lg"
                  w="full"
                  isLoading={isSubmitting || isLoginLoading}
                  loadingText="Входим..."
                  mt={2}
                >
                  Войти
                </GradientButton>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text fontSize="sm" color="slate.500">
                Нет аккаунта?{' '}
                <Link
                  as={RouterLink}
                  to="/register"
                  fontWeight={600}
                  sx={{
                    backgroundImage:
                      'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    color: 'transparent',
                  }}
                >
                  Зарегистрироваться
                </Link>
              </Text>
            </Box>
          </Stack>
        </GlassCard>
      </Flex>
    </Box>
  );
};

export default LoginPage;
