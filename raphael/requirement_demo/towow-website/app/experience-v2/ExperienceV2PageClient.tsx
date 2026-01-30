'use client';

import { useCallback } from 'react';
import { useExperienceContext } from '@/context/ExperienceContext';
import { useAuth } from '@/hooks/useAuth';
import { LoginPanel } from '@/components/experience/LoginPanel';
import { LoadingScreen } from '@/components/experience/LoadingScreen';
import { ExperienceV2Page } from '@/components/experience-v2';

export function ExperienceV2PageClient() {
  const { state, dispatch } = useExperienceContext();
  const { login, isLoading: authLoading } = useAuth();

  const handleLogin = useCallback(async () => {
    try {
      await login();
    } catch (err) {
      dispatch({
        type: 'SET_ERROR',
        payload: err instanceof Error ? err : new Error('Login failed'),
      });
      dispatch({ type: 'SET_STATE', payload: 'ERROR' });
    }
  }, [login, dispatch]);

  // Show loading screen during initial auth check
  if (state.state === 'INIT' && state.isLoading) {
    return <LoadingScreen message="检查登录状态..." />;
  }

  // Show login panel if not authenticated
  if (state.state === 'LOGIN' || state.state === 'INIT') {
    return <LoginPanel onLoginClick={handleLogin} isLoading={authLoading} />;
  }

  // User is authenticated, show the V2 demo
  return <ExperienceV2Page />;
}
