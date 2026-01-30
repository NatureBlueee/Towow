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
import { User } from '@/types/experience';
import styles from './page.module.css';

// UserHeader component - 右上角用户信息
interface UserHeaderProps {
  user: User | null;
  onLogout: () => void;
}

function UserHeader({ user, onLogout }: UserHeaderProps) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  if (!user) return null;

  return (
    <div className={styles.userHeader}>
      <div className={styles.userHeaderMain}>
        <div className={styles.userAvatar}>
          {user.avatar_url ? (
            <img src={user.avatar_url} alt={user.display_name} />
          ) : (
            <span>{user.display_name.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <span className={styles.userName}>{user.display_name}</span>
        <button
          className={styles.profileToggle}
          onClick={() => setIsProfileOpen(!isProfileOpen)}
          aria-expanded={isProfileOpen}
          aria-label={isProfileOpen ? '收起资料' : '展开资料'}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={isProfileOpen ? styles.rotated : ''}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <button className={styles.logoutButton} onClick={onLogout}>
          登出
        </button>
      </div>

      {/* Profile Card - 可折叠 */}
      {isProfileOpen && (
        <div className={styles.profileCard}>
          <div className={styles.profileSection}>
            <h4 className={styles.profileSectionTitle}>基本信息</h4>
            <div className={styles.profileInfo}>
              {user.bio && (
                <p className={styles.profileBio}>{user.bio}</p>
              )}
              <div className={styles.profileMeta}>
                <span className={styles.profileLabel}>SecondMe ID</span>
                <span className={styles.profileValue}>{user.secondme_id || '未绑定'}</span>
              </div>
            </div>
          </div>

          {user.skills && user.skills.length > 0 && (
            <div className={styles.profileSection}>
              <h4 className={styles.profileSectionTitle}>技能</h4>
              <div className={styles.tagList}>
                {user.skills.map((skill, index) => (
                  <span key={index} className={styles.skillTag}>{skill}</span>
                ))}
              </div>
            </div>
          )}

          {user.specialties && user.specialties.length > 0 && (
            <div className={styles.profileSection}>
              <h4 className={styles.profileSectionTitle}>专长领域</h4>
              <div className={styles.tagList}>
                {user.specialties.map((specialty, index) => (
                  <span key={index} className={styles.specialtyTag}>{specialty}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
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
        <ContentCard className={styles.formCard}>
          <h2 className={styles.formTitle}>提交你的需求</h2>
          <p className={styles.formDescription}>
            描述你的需求，AI Agent 们将协商出最佳方案。
          </p>
          <RequirementForm
            onSubmit={handleSubmit}
            isSubmitting={negotiationLoading}
          />
        </ContentCard>
      );
    }

    // Submitting state
    if (state.state === 'SUBMITTING') {
      return <LoadingScreen message="Submitting your requirement..." />;
    }

    // Negotiating state
    if (state.state === 'NEGOTIATING') {
      return (
        <div className={styles.negotiationContent}>
          <div className={styles.requirementSummary}>
            <h3>你的需求</h3>
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

  // 判断是否显示用户头部（登录后的状态）
  const showUserHeader = state.user && !['INIT', 'LOGIN', 'REGISTERING', 'ERROR'].includes(state.state);

  return (
    <div className={styles.container}>
      {/* 右上角用户信息 */}
      {showUserHeader && (
        <UserHeader user={state.user} onLogout={logout} />
      )}

      <header className={styles.header}>
        <h1>ToWow Experience</h1>
        <p>体验 AI Agent 协作网络</p>
      </header>

      <section className={styles.content}>{renderContent()}</section>
    </div>
  );
}
