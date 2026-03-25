import axios, { type AxiosInstance,type AxiosResponse,type InternalAxiosRequestConfig } from 'axios';
import { type TokenResponse,type  LoginRequest,type  RegisterRequest,type  User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Create axios instance
export const authApi: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Token management
export class TokenManager {
  static getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  static getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  static setTokens(tokens: TokenResponse): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }

  static clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  static isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp < currentTime;
    } catch {
      return true;
    }
  }
}

// Request interceptor to add auth token
authApi.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = TokenManager.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
authApi.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = TokenManager.getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const newTokens = response.data;
          TokenManager.setTokens(newTokens);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newTokens.access_token}`;
          return authApi(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          TokenManager.clearTokens();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token, redirect to login
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API functions
export const authService = {
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await authApi.post<TokenResponse>('/auth/login', data);
    TokenManager.setTokens(response.data);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await authApi.post<TokenResponse>('/auth/register', data);
    TokenManager.setTokens(response.data);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await authApi.get<User>('/auth/me');
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await authApi.post('/auth/logout');
    } finally {
      TokenManager.clearTokens();
    }
  },

  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = TokenManager.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });

    TokenManager.setTokens(response.data);
    return response.data;
  },

  isAuthenticated(): boolean {
    const token = TokenManager.getAccessToken();
    return token !== null && !TokenManager.isTokenExpired(token);
  },

  getCurrentUserFromStorage(): User | null {
    // This would typically come from a context/state management
    // For now, return null - will be implemented with auth context
    return null;
  },
};
