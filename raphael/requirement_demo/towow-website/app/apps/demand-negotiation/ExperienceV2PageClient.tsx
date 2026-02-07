'use client';

import { useCallback, useState } from 'react';
import { useExperienceContext } from '@/context/ExperienceContext';
import { useAuth } from '@/hooks/useAuth';
import { LoginPanel } from '@/components/shared/LoginPanel';
import { LoadingScreen } from '@/components/shared/LoadingScreen';
import { ErrorPanel } from '@/components/shared/ErrorPanel';
import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import { ExperienceV2Page } from '@/components/demand-negotiation';
import styles from '../../experience/experience.module.css';

// Registration Form for new users
interface RegistrationFormProps {
  pendingAuth: {
    name: string;
    avatar: string | null;
    bio: string | null;
    user_identifier: string;
  };
  onSubmit: (data: { displayName: string; skills: string[]; specialties?: string[]; bio?: string }) => Promise<void>;
  isLoading: boolean;
}

function RegistrationForm({ pendingAuth, onSubmit, isLoading }: RegistrationFormProps) {
  const [displayName, setDisplayName] = useState(pendingAuth.name || '');
  const [skills, setSkills] = useState('');
  const [specialties, setSpecialties] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const skillsList = skills.split(',').map(s => s.trim()).filter(Boolean);
    const specialtiesList = specialties.split(',').map(s => s.trim()).filter(Boolean);

    if (skillsList.length === 0) {
      alert('请至少填写一个技能');
      return;
    }

    await onSubmit({
      displayName,
      skills: skillsList,
      specialties: specialtiesList,
      bio: pendingAuth.bio || undefined,
    });
  };

  return (
    <ContentCard className={styles.formCard}>
      <div className={styles.registrationHeader}>
        {pendingAuth.avatar && (
          <img src={pendingAuth.avatar} alt={pendingAuth.name} className={styles.registrationAvatar} />
        )}
        <h2 className={styles.formTitle}>完成注册</h2>
        <p className={styles.formDescription}>
          欢迎 {pendingAuth.name}！请填写您的技能信息以完成 Agent 注册。
        </p>
      </div>

      <form onSubmit={handleSubmit} className={styles.registrationForm}>
        <div className={styles.formGroup}>
          <label htmlFor="displayName">显示名称</label>
          <input
            id="displayName"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            placeholder="您的显示名称"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="skills">技能 *</label>
          <input
            id="skills"
            type="text"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            required
            placeholder="例如：Python, React, 产品设计（用逗号分隔）"
          />
          <span className={styles.formHint}>请用逗号分隔多个技能</span>
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="specialties">专长领域</label>
          <input
            id="specialties"
            type="text"
            value={specialties}
            onChange={(e) => setSpecialties(e.target.value)}
            placeholder="例如：Web开发, AI产品（用逗号分隔）"
          />
        </div>

        <Button type="submit" variant="primary" disabled={isLoading}>
          {isLoading ? '注册中...' : '完成注册'}
        </Button>
      </form>
    </ContentCard>
  );
}

export function ExperienceV2PageClient() {
  const { state, dispatch } = useExperienceContext();
  const { login, isLoading: authLoading, pendingAuth, completeRegistration } = useAuth();

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

  const handleRetry = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
    dispatch({ type: 'SET_STATE', payload: state.user ? 'READY' : 'LOGIN' });
  }, [dispatch, state.user]);

  const handleReset = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
    dispatch({ type: 'SET_STATE', payload: 'LOGIN' });
  }, [dispatch]);

  // Show loading screen during initial auth check
  if (state.state === 'INIT' && state.isLoading) {
    return <LoadingScreen message="检查登录状态..." />;
  }

  // Error state
  if (state.state === 'ERROR') {
    return (
      <ErrorPanel
        title="发生错误"
        message={state.error?.message || '出了点问题'}
        onRetry={handleRetry}
        onReset={handleReset}
      />
    );
  }

  // Show login panel if not authenticated
  if (state.state === 'LOGIN' || state.state === 'INIT') {
    return <LoginPanel onLoginClick={handleLogin} isLoading={authLoading} />;
  }

  // Registration state - new user needs to complete registration
  if (state.state === 'REGISTERING' && pendingAuth) {
    return (
      <RegistrationForm
        pendingAuth={pendingAuth}
        onSubmit={completeRegistration}
        isLoading={state.isLoading}
      />
    );
  }

  // User is authenticated (READY state or later), show the V2 demo
  return <ExperienceV2Page />;
}
