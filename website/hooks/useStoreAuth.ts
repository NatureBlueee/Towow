'use client';

import { useState, useEffect, useCallback } from 'react';
import { getCurrentUser, logout as logoutApi } from '@/lib/api/auth';
import { handleApiError, type ApiError } from '@/lib/errors';

export type AuthSource = 'secondme' | 'local' | null;

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
  authSource: AuthSource;
  login: () => void;
  logout: () => Promise<void>;
  error: ApiError | null;
  clearError: () => void;
}

const LOCAL_AGENT_KEY = 'playground_agent_id';
const LOCAL_NAME_KEY = 'playground_display_name';

export function useStoreAuth(): UseStoreAuthReturn {
  const [user, setUser] = useState<StoreUser | null>(null);
  const [authSource, setAuthSource] = useState<AuthSource>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    try {
      // 1. Try cookie session (SecondMe)
      const data = await getCurrentUser();
      if (data) {
        setUser(data);
        setAuthSource('secondme');
        setIsLoading(false);
        return;
      }
    } catch (err) {
      const apiError = handleApiError(err);
      if (apiError.code !== 'HTTP_401') {
        setError(apiError);
      }
    }

    // 2. Fallback: check localStorage (Playground / email / phone registration)
    try {
      const localAgentId = localStorage.getItem(LOCAL_AGENT_KEY);
      const localName = localStorage.getItem(LOCAL_NAME_KEY);
      if (localAgentId) {
        setUser({ agent_id: localAgentId, display_name: localName || '' });
        setAuthSource('local');
        setIsLoading(false);
        return;
      }
    } catch {
      // localStorage unavailable (SSR, privacy mode) — ignore
    }

    // 3. No auth
    setUser(null);
    setAuthSource(null);
    setIsLoading(false);
  }, []);

  const login = useCallback(() => {
    setError(null);
    window.location.href = '/enter';
  }, []);

  const logout = useCallback(async () => {
    setError(null);
    try {
      await logoutApi();
    } catch {
      // Cookie logout failure is non-fatal (may not have cookie)
    }
    // Always clear localStorage
    try {
      localStorage.removeItem(LOCAL_AGENT_KEY);
      localStorage.removeItem(LOCAL_NAME_KEY);
    } catch {
      // localStorage unavailable — ignore
    }
    setUser(null);
    setAuthSource(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    authSource,
    login,
    logout,
    error,
    clearError,
  };
}
