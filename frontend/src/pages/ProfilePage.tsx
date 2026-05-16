import { useEffect, useState } from 'react';
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
  Select,
  SimpleGrid,
  Stack,
  Text,
  useToast,
} from '@chakra-ui/react';
import { useAuth } from '@/features/auth';
import { GlassCard } from '@/components/ui/GlassCard';
import { GradientButton } from '@/components/ui/GradientButton';
import { LANGUAGES } from '@/types/letter';

const UI_LANG_KEY = 'aurora.uiLang';
const DEFAULT_GEN_LANG_KEY = 'aurora.defaultGenLang';

type UiLang = 'ru' | 'en';

const profileSchema = z.object({
  first_name: z.string().min(1, 'Введите имя'),
  last_name: z.string().min(1, 'Введите фамилию'),
  email: z.string().email('Неверный email адрес'),
});
type ProfileFormData = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current_password: z.string().min(8, 'Минимум 8 символов'),
    new_password: z.string().min(8, 'Минимум 8 символов'),
    confirm_password: z.string().min(8, 'Минимум 8 символов'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Пароли не совпадают',
    path: ['confirm_password'],
  });
type PasswordFormData = z.infer<typeof passwordSchema>;

function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <Box mb={6}>
      <Heading
        fontFamily="heading"
        fontSize="xl"
        fontWeight={600}
        color="slate.900"
        letterSpacing="-0.01em"
        mb={1}
      >
        {title}
      </Heading>
      {subtitle && (
        <Text color="slate.500" fontSize="sm">
          {subtitle}
        </Text>
      )}
    </Box>
  );
}

function UiLangToggle({ value, onChange }: { value: UiLang; onChange: (v: UiLang) => void }) {
  const options: { code: UiLang; label: string }[] = [
    { code: 'ru', label: 'Русский' },
    { code: 'en', label: 'English' },
  ];
  return (
    <Flex
      position="relative"
      bg="rgba(255,255,255,0.5)"
      borderRadius="full"
      p={1}
      border="1px solid"
      borderColor="slate.200"
      w="fit-content"
      gap={1}
    >
      {options.map((o) => {
        const active = o.code === value;
        return (
          <Box
            key={o.code}
            as="button"
            type="button"
            onClick={() => onChange(o.code)}
            px={5}
            py={2}
            borderRadius="full"
            fontSize="sm"
            fontWeight={600}
            color={active ? 'white' : 'slate.700'}
            transition="color 180ms ease"
            sx={
              active
                ? {
                    backgroundImage:
                      'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)',
                    boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
                  }
                : undefined
            }
            _hover={!active ? { color: 'slate.900' } : undefined}
          >
            {o.label}
          </Box>
        );
      })}
    </Flex>
  );
}

function PersonalInfoCard() {
  const { user, updateProfile, isUpdateProfileLoading } = useAuth();
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      email: user?.email ?? '',
    },
  });

  useEffect(() => {
    if (user) {
      reset({
        first_name: user.first_name ?? '',
        last_name: user.last_name ?? '',
        email: user.email ?? '',
      });
    }
  }, [user, reset]);

  const onSubmit = async (data: ProfileFormData) => {
    try {
      await updateProfile(data);
      toast({
        title: 'Профиль обновлён',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Не удалось обновить профиль',
        description: err instanceof Error ? err.message : 'Попробуйте ещё раз',
        status: 'error',
        duration: 3500,
        isClosable: true,
      });
    }
  };

  return (
    <GlassCard padding={{ base: 6, md: 8 }}>
      <SectionHeading
        title="Личная информация"
        subtitle="Имя и email, которые видит система"
      />
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack spacing={5}>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl isInvalid={!!errors.first_name}>
              <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                Имя
              </FormLabel>
              <Input {...register('first_name')} />
              <FormErrorMessage>{errors.first_name?.message}</FormErrorMessage>
            </FormControl>
            <FormControl isInvalid={!!errors.last_name}>
              <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                Фамилия
              </FormLabel>
              <Input {...register('last_name')} />
              <FormErrorMessage>{errors.last_name?.message}</FormErrorMessage>
            </FormControl>
          </SimpleGrid>
          <FormControl isInvalid={!!errors.email}>
            <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
              Email
            </FormLabel>
            <Input type="email" autoComplete="email" {...register('email')} />
            <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
          </FormControl>
          <Flex justify="flex-end" pt={2}>
            <GradientButton
              type="submit"
              isLoading={isSubmitting || isUpdateProfileLoading}
              loadingText="Сохраняем..."
              isDisabled={!isDirty}
            >
              Сохранить изменения
            </GradientButton>
          </Flex>
        </Stack>
      </form>
    </GlassCard>
  );
}

function PasswordCard() {
  const { changePassword, isChangePasswordLoading } = useAuth();
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onSubmit = async (data: PasswordFormData) => {
    try {
      await changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      });
      toast({
        title: 'Пароль обновлён',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
      reset();
    } catch (err) {
      toast({
        title: 'Не удалось сменить пароль',
        description: err instanceof Error ? err.message : 'Проверьте текущий пароль',
        status: 'error',
        duration: 3500,
        isClosable: true,
      });
    }
  };

  return (
    <GlassCard padding={{ base: 6, md: 8 }}>
      <SectionHeading
        title="Пароль"
        subtitle="Минимум 8 символов. Используйте уникальную фразу"
      />
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack spacing={5}>
          <FormControl isInvalid={!!errors.current_password}>
            <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
              Текущий пароль
            </FormLabel>
            <Input
              type="password"
              autoComplete="current-password"
              {...register('current_password')}
            />
            <FormErrorMessage>{errors.current_password?.message}</FormErrorMessage>
          </FormControl>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl isInvalid={!!errors.new_password}>
              <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                Новый пароль
              </FormLabel>
              <Input
                type="password"
                autoComplete="new-password"
                {...register('new_password')}
              />
              <FormErrorMessage>{errors.new_password?.message}</FormErrorMessage>
            </FormControl>
            <FormControl isInvalid={!!errors.confirm_password}>
              <FormLabel fontSize="sm" color="slate.700" fontWeight={500}>
                Подтверждение
              </FormLabel>
              <Input
                type="password"
                autoComplete="new-password"
                {...register('confirm_password')}
              />
              <FormErrorMessage>{errors.confirm_password?.message}</FormErrorMessage>
            </FormControl>
          </SimpleGrid>
          <Flex justify="flex-end" pt={2}>
            <GradientButton
              type="submit"
              isLoading={isSubmitting || isChangePasswordLoading}
              loadingText="Обновляем..."
            >
              Обновить пароль
            </GradientButton>
          </Flex>
        </Stack>
      </form>
    </GlassCard>
  );
}

function PreferencesCard() {
  const [uiLang, setUiLang] = useState<UiLang>('ru');
  const [defaultGenLang, setDefaultGenLang] = useState<string>(LANGUAGES[0].code);

  useEffect(() => {
    const storedUi = localStorage.getItem(UI_LANG_KEY) as UiLang | null;
    if (storedUi === 'ru' || storedUi === 'en') setUiLang(storedUi);
    const storedGen = localStorage.getItem(DEFAULT_GEN_LANG_KEY);
    if (storedGen && LANGUAGES.some((l) => l.code === storedGen)) {
      setDefaultGenLang(storedGen);
    }
  }, []);

  const onUiLangChange = (v: UiLang) => {
    setUiLang(v);
    localStorage.setItem(UI_LANG_KEY, v);
  };

  const onGenLangChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value;
    setDefaultGenLang(v);
    localStorage.setItem(DEFAULT_GEN_LANG_KEY, v);
  };

  return (
    <GlassCard padding={{ base: 6, md: 8 }}>
      <SectionHeading
        title="Предпочтения"
        subtitle="Сохраняются локально на этом устройстве"
      />
      <Stack spacing={6}>
        <Box>
          <Text fontSize="sm" color="slate.700" fontWeight={500} mb={3}>
            Язык интерфейса
          </Text>
          <UiLangToggle value={uiLang} onChange={onUiLangChange} />
        </Box>
        <Box maxW="320px">
          <Text fontSize="sm" color="slate.700" fontWeight={500} mb={3}>
            Язык генерации по умолчанию
          </Text>
          <Select value={defaultGenLang} onChange={onGenLangChange}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </Select>
        </Box>
      </Stack>
    </GlassCard>
  );
}

export default function ProfilePage() {
  return (
    <Box>
      <Heading
        fontFamily="heading"
        fontSize="3xl"
        fontWeight={600}
        color="slate.900"
        letterSpacing="-0.02em"
        mb={8}
      >
        Профиль
      </Heading>
      <Stack spacing={6}>
        <PersonalInfoCard />
        <PasswordCard />
        <PreferencesCard />
      </Stack>
    </Box>
  );
}
