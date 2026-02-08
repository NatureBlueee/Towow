'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useExperienceContext } from '@/context/ExperienceContext';
import { getAuthUrl, getCurrentUser, logout as logoutApi } from '@/lib/api/auth';
import { handleApiError, OAuth2Errors, ApiError } from '@/lib/errors';

// 使用相对路径，通过 Next.js rewrites 代理到后端
const API_BASE = '';

// 是否跳过登录（用于线上演示）
const SKIP_AUTH = process.env.NEXT_PUBLIC_SKIP_AUTH === 'true';

// 模拟用户（跳过登录时使用）
const DEMO_USER = {
  agent_id: 'demo_user',
  display_name: '演示用户',
  avatar_url: undefined,
  bio: '这是一个演示账户',
  self_introduction: '欢迎体验 ToWow AI Agent 协作网络',
  profile_completeness: 100,
  skills: ['产品设计', '需求分析'],
  specialties: ['AI 产品'],
  secondme_id: 'demo',
};

interface PendingAuthData {
  name: string;
  avatar: string | null;
  bio: string | null;
  user_identifier: string;
}

interface UseAuthReturn {
  user: ReturnType<typeof useExperienceContext>['state']['user'];
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  error: ApiError | null;
  clearError: () => void;
  pendingAuth: PendingAuthData | null;
  pendingAuthId: string | null;
  pendingAuthLoading: boolean;
  completeRegistration: (data: { displayName: string; skills: string[]; specialties?: string[]; bio?: string }) => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const { state, dispatch } = useExperienceContext();
  const searchParams = useSearchParams();
  const [error, setError] = useState<ApiError | null>(null);
  const [pendingAuth, setPendingAuth] = useState<PendingAuthData | null>(null);
  const [pendingAuthId, setPendingAuthId] = useState<string | null>(null);
  const [pendingAuthLoading, setPendingAuthLoading] = useState<boolean>(false);

  // 处理 OAuth2 回调错误
  useEffect(() => {
    const oauthError = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    if (oauthError) {
      let apiError: ApiError;

      switch (oauthError) {
        case 'access_denied':
          apiError = OAuth2Errors.ACCESS_DENIED;
          break;
        case 'invalid_request':
          apiError = {
            code: 'OAUTH_INVALID_REQUEST',
            message: errorDescription || '无效的授权请求',
          };
          break;
        case 'unauthorized_client':
          apiError = {
            code: 'OAUTH_UNAUTHORIZED',
            message: '应用未被授权',
          };
          break;
        case 'server_error':
          apiError = {
            code: 'OAUTH_SERVER_ERROR',
            message: '授权服务器错误，请稍后重试',
          };
          break;
        default:
          apiError = {
            code: 'OAUTH_CALLBACK_ERROR',
            message: errorDescription || OAuth2Errors.CALLBACK_FAILED.message,
          };
      }

      setError(apiError);
      dispatch({ type: 'SET_ERROR', payload: new Error(apiError.message) });

      // 清除 URL 中的错误参数
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href);
        url.searchParams.delete('error');
        url.searchParams.delete('error_description');
        window.history.replaceState({}, '', url.toString());
      }
    }
  }, [searchParams, dispatch]);

  // 处理 pending_auth 参数（新用户需要注册）
  useEffect(() => {
    const pendingId = searchParams.get('pending_auth');
    if (pendingId) {
      setPendingAuthId(pendingId);

      // 获取待注册用户信息
      const fetchPendingAuth = async () => {
        setPendingAuthLoading(true);
        setError(null);

        try {
          const res = await fetch(`${API_BASE}/api/auth/pending/${pendingId}`);
          if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || '获取用户信息失败');
          }
          const data = await res.json();
          setPendingAuth(data);
          dispatch({ type: 'SET_STATE', payload: 'REGISTERING' });
        } catch (err) {
          console.error('Failed to fetch pending auth data:', err);
          const errorMessage = err instanceof Error ? err.message : '获取用户信息失败';
          setError({ code: 'PENDING_AUTH_ERROR', message: errorMessage });
          dispatch({ type: 'SET_ERROR', payload: new Error(errorMessage) });
        } finally {
          setPendingAuthLoading(false);
        }
      };

      fetchPendingAuth();

      // 清除 URL 中的 pending_auth 参数
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href);
        url.searchParams.delete('pending_auth');
        window.history.replaceState({}, '', url.toString());
      }
    }
  }, [searchParams, dispatch]);

  const clearError = useCallback(() => {
    setError(null);
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [dispatch]);

  const checkAuth = useCallback(async () => {
    // 如果跳过登录，直接设置演示用户
    if (SKIP_AUTH) {
      dispatch({ type: 'SET_USER', payload: DEMO_USER });
      dispatch({ type: 'SET_STATE', payload: 'READY' });
      dispatch({ type: 'SET_LOADING', payload: false });
      return;
    }

    // 如果正在处理 pending_auth，不要检查认证状态
    if (pendingAuthId || pendingAuth) return;

    dispatch({ type: 'SET_LOADING', payload: true });
    setError(null);

    try {
      const user = await getCurrentUser();
      dispatch({ type: 'SET_USER', payload: user });
      dispatch({ type: 'SET_STATE', payload: user ? 'READY' : 'LOGIN' });
    } catch (err) {
      const apiError = handleApiError(err);

      // 401 错误是正常的未登录状态，不需要显示错误
      if (apiError.code !== 'HTTP_401') {
        setError(apiError);
      }

      dispatch({ type: 'SET_USER', payload: null });
      dispatch({ type: 'SET_STATE', payload: 'LOGIN' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [dispatch, pendingAuthId, pendingAuth]);

  const login = useCallback(async () => {
    setError(null);

    try {
      const authUrl = await getAuthUrl();
      window.location.href = authUrl;
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
      dispatch({ type: 'SET_ERROR', payload: new Error(apiError.message) });
    }
  }, [dispatch]);

  const logout = useCallback(async () => {
    // 跳过登录模式下，登出只是重置状态
    if (SKIP_AUTH) {
      dispatch({ type: 'SET_USER', payload: DEMO_USER });
      dispatch({ type: 'SET_STATE', payload: 'READY' });
      return;
    }

    setError(null);

    try {
      await logoutApi();
      dispatch({ type: 'SET_USER', payload: null });
      dispatch({ type: 'SET_STATE', payload: 'LOGIN' });
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
      // 即使登出失败，也清除本地状态
      dispatch({ type: 'SET_USER', payload: null });
      dispatch({ type: 'SET_STATE', payload: 'LOGIN' });
    }
  }, [dispatch]);

  const completeRegistration = useCallback(async (data: {
    displayName: string;
    skills: string[];
    specialties?: string[];
    bio?: string;
  }) => {
    if (!pendingAuthId) {
      setError({ code: 'NO_PENDING_AUTH', message: '没有待完成的注册' });
      return;
    }

    dispatch({ type: 'SET_LOADING', payload: true });
    setError(null);

    try {
      const params = new URLSearchParams({
        display_name: data.displayName,
        skills: data.skills.join(','),
        specialties: (data.specialties || []).join(','),
        ...(data.bio && { bio: data.bio }),
      });

      const response = await fetch(
        `${API_BASE}/api/auth/pending/${pendingAuthId}/complete?${params}`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('注册失败');
      }

      const result = await response.json();

      if (result.success) {
        // 注册成功，重新检查认证状态
        setPendingAuth(null);
        setPendingAuthId(null);
        await checkAuth();
      } else {
        throw new Error(result.message || '注册失败');
      }
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
      dispatch({ type: 'SET_ERROR', payload: new Error(apiError.message) });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [pendingAuthId, dispatch, checkAuth]);

  useEffect(() => {
    // 只有在没有 pending_auth 时才检查认证状态
    const pendingId = searchParams.get('pending_auth');
    if (!pendingId) {
      checkAuth();
    }
  }, []);

  return {
    user: state.user,
    isLoading: state.isLoading,
    isAuthenticated: !!state.user,
    login,
    logout,
    checkAuth,
    error,
    clearError,
    pendingAuth,
    pendingAuthId,
    pendingAuthLoading,
    completeRegistration,
  };
}
