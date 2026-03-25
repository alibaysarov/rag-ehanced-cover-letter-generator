import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authService } from '../api/auth-client';
import type { LoginRequest, RegisterRequest, TokenResponse } from '../types';

// Query keys
export const authKeys = {
  user: ['auth', 'user'] as const,
  all: ['auth'] as const,
};

// Custom hook for authentication state
export const useAuth = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Get current user query
  const {
    data: user,
    isLoading,
    error,
    refetch: refetchUser,
  } = useQuery({
    queryKey: authKeys.user,
    queryFn: authService.getCurrentUser,
    enabled: authService.isAuthenticated(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Handle authentication errors - redirect to login
  useEffect(() => {
    // if(error) {
    //   authService.logout();
    //   navigate('/login');
    //   return
    // }
    if (error && (error as any)?.response?.status === 401 || (error as any)?.response?.status === 403) {
      authService.logout();
      // navigate('/login');
    }
  }, [error, navigate]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authService.login(data),
    onSuccess: (tokens: TokenResponse) => {
      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: (tokens: TokenResponse) => {
      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      // Clear user data from cache
      queryClient.removeQueries({ queryKey: authKeys.all });
    },
  });

  const isAuthenticated = authService.isAuthenticated();

  return {
    user,
    isAuthenticated,
    isLoading,
    error: error?.message || null,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    isLoginLoading: loginMutation.isPending,
    isRegisterLoading: registerMutation.isPending,
    isLogoutLoading: logoutMutation.isPending,
    loginError: loginMutation.error?.message || null,
    registerError: registerMutation.error?.message || null,
    logoutError: logoutMutation.error?.message || null,
    refetchUser,
  };
};
