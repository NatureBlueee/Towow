'use client';

import { useCallback, useState } from 'react';
import { useExperienceContext } from '@/context/ExperienceContext';
import { useAuth } from '@/hooks/useAuth';
import { useNegotiation } from '@/hooks/useNegotiation';
import { LoginPanel } from '@/components/experience/LoginPanel';
import { RequirementForm } from '@/components/experience/RequirementForm';
import { NegotiationTimeline } from '@/components/experience/NegotiationTimeline';
import { ResultPanel } from '@/components/experience/ResultPanel';
import { ErrorPanel } from '@/components/experience/ErrorPanel';
import { LoadingScreen } from '@/components/experience/LoadingScreen';
import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import styles from './page.module.css';

// UserInfo component
interface UserInfoProps {
  user: {
    display_name: string;
    avatar_url?: string;
    bio?: string;
  } | null;
  onLogout: () => void;
}

function UserInfo({ user, onLogout }: UserInfoProps) {
  if (!user) return null;

  return (
    <div className={styles.userInfo}>
      <div className={styles.userAvatar}>
        {user.avatar_url ? (
          <img src={user.avatar_url} alt={user.display_name} />
        ) : (
          <span>{user.display_name.charAt(0).toUpperCase()}</span>
        )}
      </div>
      <div className={styles.userDetails}>
        <span className={styles.userName}>{user.display_name}</span>
        {user.bio && <span className={styles.userBio}>{user.bio}</span>}
      </div>
      <button className={styles.logoutButton} onClick={onLogout}>
        Logout
      </button>
    </div>
  );
}

// Registration Form component
interface RegistrationFormProps {
  pendingAuth: {
    name: string;
    avatar: string | null;
    bio: string | null;
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

export function ExperiencePageClient() {
  const { state, dispatch } = useExperienceContext();
  const { login, logout, isLoading: authLoading, pendingAuth, completeRegistration } = useAuth();
  const {
    submitRequirement,
    currentRequirement,
    negotiationStatus,
    messages,
    result,
    isLoading: negotiationLoading,
    reset,
  } = useNegotiation();

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

  const handleSubmit = useCallback(
    async (data: { title: string; description: string }) => {
      try {
        await submitRequirement(data);
      } catch (err) {
        dispatch({
          type: 'SET_ERROR',
          payload: err instanceof Error ? err : new Error('Submit failed'),
        });
        dispatch({ type: 'SET_STATE', payload: 'ERROR' });
      }
    },
    [submitRequirement, dispatch]
  );

  const handleReset = useCallback(() => {
    reset();
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [reset, dispatch]);

  const handleRetry = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
    dispatch({ type: 'SET_STATE', payload: state.user ? 'READY' : 'LOGIN' });
  }, [dispatch, state.user]);

  // Render based on current state
  const renderContent = () => {
    // Show loading screen during initial auth check
    if (state.state === 'INIT' && state.isLoading) {
      return <LoadingScreen message="Initializing..." />;
    }

    // Error state
    if (state.state === 'ERROR') {
      return (
        <ErrorPanel
          title="An error occurred"
          message={state.error?.message || 'Something went wrong'}
          onRetry={handleRetry}
          onReset={handleReset}
        />
      );
    }

    // Login state
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

    // Ready state - show requirement form
    if (state.state === 'READY') {
      return (
        <div className={styles.readyContainer}>
          <UserInfo user={state.user} onLogout={logout} />
          <ContentCard className={styles.formCard}>
            <h2 className={styles.formTitle}>Submit Your Requirement</h2>
            <p className={styles.formDescription}>
              Describe what you need, and our AI agents will negotiate the best
              solution.
            </p>
            <RequirementForm
              onSubmit={handleSubmit}
              isSubmitting={negotiationLoading}
            />
          </ContentCard>
        </div>
      );
    }

    // Submitting state
    if (state.state === 'SUBMITTING') {
      return <LoadingScreen message="Submitting your requirement..." />;
    }

    // Negotiating state
    if (state.state === 'NEGOTIATING') {
      return (
        <div className={styles.negotiatingContainer}>
          <UserInfo user={state.user} onLogout={logout} />
          <div className={styles.negotiationContent}>
            <div className={styles.requirementSummary}>
              <h3>Your Requirement</h3>
              <p>{currentRequirement?.requirement_text}</p>
            </div>
            <NegotiationTimeline
              messages={messages}
              status={
                negotiationStatus === 'in_progress' ? 'in_progress' : 'waiting'
              }
              isLoading={negotiationStatus === 'waiting'}
              currentUserId={state.user?.agent_id}
            />
          </div>
        </div>
      );
    }

    // Completed state
    if (state.state === 'COMPLETED') {
      return (
        <ResultPanel
          status={result?.status || 'completed'}
          summary={result?.summary || 'Negotiation completed successfully'}
          participants={result?.participants}
          finalProposal={result?.final_proposal}
          onReset={handleReset}
        />
      );
    }

    // Fallback
    return <LoadingScreen message="Loading..." />;
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>ToWow Experience</h1>
        <p>Experience AI Agent Collaboration Network</p>
      </header>

      <section className={styles.content}>{renderContent()}</section>
    </div>
  );
}
