'use client';

import { useState, useEffect, useCallback } from 'react';
import { getAuthUrl, getCurrentUser, logout as logoutApi } from '@/lib/api/auth';
import { handleApiError, type ApiError } from '@/lib/errors';

export interface StoreUser {
  agent_id: string;
  display_name: string;
  avatar_url?: string;
  bio?: string;
  skills?: string[];
}

interface UseStoreAuthReturn {
  user: StoreUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => Promise<void>;
  error: ApiError | null;
  clearError: () => void;
}

export function useStoreAuth(): UseStoreAuthReturn {
  const [user, setUser] = useState<StoreUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getCurrentUser();
      setUser(data);
    } catch (err) {
      const apiError = handleApiError(err);
      if (apiError.code !== 'HTTP_401') {
        setError(apiError);
      }
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(() => {
    setError(null);
    window.location.href = getAuthUrl('/store/');
  }, []);

  const logout = useCallback(async () => {
    setError(null);
    try {
      await logoutApi();
      setUser(null);
    } catch (err) {
      setError(handleApiError(err));
      setUser(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    error,
    clearError,
  };
}
