'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { TagInput } from './TagInput';
import {
  SKILL_OPTIONS,
  ROLE_OPTIONS,
  AVAILABILITY_OPTIONS,
  TeamRequestFormData,
} from '@/lib/team-matcher/types';
import { createTeamRequest, getFormSuggestions } from '@/lib/team-matcher/api';
import type { FormSuggestions } from '@/lib/team-matcher/api';
import { getAuthUrl } from '@/lib/api/auth';
import { useTeamAuth } from '@/context/TeamAuthContext';
import styles from './TeamRequestForm.module.css';

export function TeamRequestForm() {
  const router = useRouter();
  const { user, isChecking, isAuthenticated } = useTeamAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [formData, setFormData] = useState<TeamRequestFormData>({
    project_idea: '',
    skills: [],
    availability: '',
    roles_needed: [],
  });

  // SecondMe suggestion state
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestMessage, setSuggestMessage] = useState<string | null>(null);
  const hasAutoFilledRef = useRef(false);
  const typewriterRef = useRef<ReturnType<typeof setInterval>[]>([]);

  const isValid =
    formData.project_idea.trim().length > 10 &&
    formData.skills.length > 0 &&
    formData.availability !== '';

  const [loginError, setLoginError] = useState<string | null>(null);

  // Cleanup typewriter intervals on unmount
  useEffect(() => {
    return () => {
      typewriterRef.current.forEach(clearInterval);
    };
  }, []);

  // Auto-suggest when user becomes authenticated
  useEffect(() => {
    if (!isAuthenticated || hasAutoFilledRef.current || isSuggesting) return;

    let cancelled = false;

    const fetchSuggestions = async () => {
      setIsSuggesting(true);
      try {
        const result = await getFormSuggestions();
        if (cancelled) return;

        if (result.success && result.suggestions) {
          setSuggestMessage(result.message);
          applyAutoFill(result.suggestions);
        } else if (result.error !== 'not_authenticated') {
          // Show message even on failure (friendly fallback)
          if (result.message) setSuggestMessage(result.message);
        }
      } catch (err) {
        console.error('Failed to get suggestions:', err);
      } finally {
        if (!cancelled) {
          setIsSuggesting(false);
          hasAutoFilledRef.current = true;
        }
      }
    };

    fetchSuggestions();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  /**
   * Auto-fill form fields with typewriter effect for project_idea
   * and staggered additions for skills/roles.
   * Only fills empty fields — respects user input.
   */
  const applyAutoFill = useCallback((suggestions: FormSuggestions) => {
    const { project_idea, skills, availability, roles_needed } = suggestions;
    let totalDelay = 0;

    // project_idea: typewriter effect (only if field is empty)
    if (project_idea) {
      let i = 0;
      const interval = setInterval(() => {
        setFormData(prev => {
          // Stop if user has manually typed something different
          if (prev.project_idea.length > i && prev.project_idea !== project_idea.slice(0, prev.project_idea.length)) {
            clearInterval(interval);
            return prev;
          }
          return { ...prev, project_idea: project_idea.slice(0, i + 1) };
        });
        i++;
        if (i >= project_idea.length) clearInterval(interval);
      }, 20);
      typewriterRef.current.push(interval);
      totalDelay = project_idea.length * 20 + 300;
    }

    // skills: add one by one
    if (skills.length > 0) {
      skills.forEach((skill, index) => {
        const timer = setTimeout(() => {
          setFormData(prev => {
            if (prev.skills.length > 0) return prev; // user already added skills
            return { ...prev, skills: [...new Set([...prev.skills, skill])] };
          });
        }, totalDelay + index * 200);
        typewriterRef.current.push(timer as unknown as ReturnType<typeof setInterval>);
      });
      totalDelay += skills.length * 200 + 200;
    }

    // availability: set directly
    if (availability) {
      const timer = setTimeout(() => {
        setFormData(prev => {
          if (prev.availability) return prev; // user already selected
          return { ...prev, availability };
        });
      }, totalDelay);
      typewriterRef.current.push(timer as unknown as ReturnType<typeof setInterval>);
      totalDelay += 300;
    }

    // roles_needed: add one by one
    if (roles_needed.length > 0) {
      roles_needed.forEach((role, index) => {
        const timer = setTimeout(() => {
          setFormData(prev => {
            if (prev.roles_needed.length > 0) return prev; // user already added roles
            return { ...prev, roles_needed: [...new Set([...prev.roles_needed, role])] };
          });
        }, totalDelay + index * 200);
        typewriterRef.current.push(timer as unknown as ReturnType<typeof setInterval>);
      });
    }
  }, []);

  const handleLogin = useCallback(async () => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const authUrl = await getAuthUrl('/apps/team-matcher/request');
      if (!authUrl) {
        throw new Error('未获取到登录地址');
      }
      window.location.href = authUrl;
    } catch (err) {
      console.error('Failed to get auth URL:', err);
      setLoginError('无法连接后端服务，请确认后端已启动');
      setIsLoggingIn(false);
    }
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || isSubmitting) return;

      setIsSubmitting(true);
      try {
        const response = await createTeamRequest({
          ...formData,
          user_id: user?.agent_id || 'anonymous',
        });
        router.push(`/apps/team-matcher/progress/${response.request_id}`);
      } catch (err) {
        console.error('Failed to create team request:', err);
        setIsSubmitting(false);
      }
    },
    [formData, isValid, isSubmitting, router, user]
  );

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <i className="ri-signal-tower-line" />
        </div>
        <h1 className={styles.title}>发出你的信号</h1>
        <p className={styles.subtitle}>
          描述你的项目想法和你能带来的技能，让共振找到你的伙伴
        </p>
      </div>

      {/* Login prompt */}
      {!isChecking && !isAuthenticated && (
        <div className={styles.loginPrompt}>
          <div className={styles.loginPromptIcon}>
            <i className="ri-user-line" />
          </div>
          <div className={styles.loginPromptText}>
            <p className={styles.loginPromptTitle}>登录以获得完整体验</p>
            <p className={styles.loginPromptDesc}>
              登录 SecondMe 后，AI 将基于你的 Profile 自动填写表单
            </p>
          </div>
          <button
            type="button"
            className={styles.loginBtn}
            onClick={handleLogin}
            disabled={isLoggingIn}
          >
            {isLoggingIn ? (
              <>
                <span className={styles.submitSpinner} />
                跳转中...
              </>
            ) : (
              <>
                <i className="ri-login-box-line" />
                登录 SecondMe
              </>
            )}
          </button>
          {loginError && (
            <p className={styles.loginError}>{loginError}</p>
          )}
        </div>
      )}

      {/* SecondMe suggesting state */}
      {isAuthenticated && isSuggesting && (
        <div className={styles.suggestingBanner}>
          <div className={styles.suggestingPulse} />
          <span>你的 SecondMe 正在思考...</span>
        </div>
      )}

      {/* SecondMe message bubble (after suggestion completes) */}
      {isAuthenticated && !isSuggesting && suggestMessage && (
        <div className={styles.secondMeMessage}>
          <div className={styles.secondMeAvatar}>
            <i className="ri-robot-2-line" />
          </div>
          <div className={styles.secondMeBubble}>
            <p className={styles.secondMeLabel}>你的 SecondMe</p>
            <p className={styles.secondMeText}>{suggestMessage}</p>
          </div>
        </div>
      )}

      {/* Logged-in indicator (fallback when no suggest message) */}
      {isAuthenticated && user && !isSuggesting && !suggestMessage && (
        <div className={styles.loggedInBanner}>
          <i className="ri-checkbox-circle-line" />
          <span>已登录为 {user.display_name}</span>
        </div>
      )}

      {/* Project Idea */}
      <div className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="project-idea">
          <i className="ri-lightbulb-line" />
          项目想法
        </label>
        <textarea
          id="project-idea"
          className={styles.textarea}
          placeholder="描述你想做的项目... 比如：一个用 AI 分析饮食数据并给出个性化健康建议的应用"
          value={formData.project_idea}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, project_idea: e.target.value }))
          }
          maxLength={500}
          rows={4}
        />
        <div className={styles.charCount}>
          <span>{formData.project_idea.length}</span> / 500
        </div>
      </div>

      {/* My Skills */}
      <div className={styles.field}>
        <div className={styles.fieldLabelRow}>
          <i className="ri-tools-line" />
          <span>我的技能</span>
        </div>
        <TagInput
          label=""
          value={formData.skills}
          onChange={(skills) => setFormData((prev) => ({ ...prev, skills }))}
          suggestions={SKILL_OPTIONS}
          placeholder="选择或输入你的技能..."
          maxTags={8}
          hint="选择你擅长的技能，团队组合时会用到"
        />
      </div>

      {/* Available Time */}
      <div className={styles.field}>
        <label className={styles.fieldLabel}>
          <i className="ri-time-line" />
          可用时间
        </label>
        <div className={styles.radioGroup}>
          {AVAILABILITY_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`${styles.radioCard} ${
                formData.availability === opt.value ? styles.radioCardActive : ''
              }`}
            >
              <input
                type="radio"
                name="available_time"
                value={opt.value}
                checked={formData.availability === opt.value}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    availability: e.target.value,
                  }))
                }
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Roles Needed */}
      <div className={styles.field}>
        <div className={styles.fieldLabelRow}>
          <i className="ri-group-line" />
          <span>我在找</span>
          <span className={styles.fieldHint}>不确定也没关系</span>
        </div>
        <TagInput
          label=""
          value={formData.roles_needed}
          onChange={(roles_needed) =>
            setFormData((prev) => ({ ...prev, roles_needed }))
          }
          suggestions={ROLE_OPTIONS}
          placeholder="期望的队友角色（可选）..."
          maxTags={5}
          hint="留空也可以，系统会帮你发现意想不到的组合"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        className={`${styles.submitBtn} ${isValid ? styles.submitBtnReady : ''}`}
        disabled={!isValid || isSubmitting}
      >
        {isSubmitting ? (
          <>
            <span className={styles.submitSpinner} />
            信号发送中...
          </>
        ) : (
          <>
            <i className="ri-radar-line" />
            发出信号
          </>
        )}
      </button>

      <p className={styles.submitHint}>
        信号发出后，系统会广播给网络中的所有 Agent，等待它们的响应
      </p>
    </form>
  );
}
