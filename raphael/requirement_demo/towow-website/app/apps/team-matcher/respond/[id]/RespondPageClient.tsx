'use client';

import { useState, useEffect, useCallback } from 'react';
import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { TagInput } from '@/components/team-matcher/TagInput';
import {
  SKILL_OPTIONS,
  AVAILABILITY_OPTIONS,
} from '@/lib/team-matcher/types';
import type { TeamRequestDetail } from '@/lib/team-matcher/types';
import { getTeamRequest, submitTeamOffer } from '@/lib/team-matcher/api';
import { getAuthUrl } from '@/lib/api/auth';
import { useTeamAuth } from '@/context/TeamAuthContext';
import styles from './RespondPage.module.css';

interface RespondPageClientProps {
  requestId: string;
}

interface OfferFormData {
  role: string;
  skills: string[];
  motivation: string;
  availability: string;
}

export function RespondPageClient({ requestId }: RespondPageClientProps) {
  const { user, isChecking, isAuthenticated } = useTeamAuth();

  // Request details
  const [request, setRequest] = useState<TeamRequestDetail | null>(null);
  const [loadingRequest, setLoadingRequest] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<OfferFormData>({
    role: '',
    skills: [],
    motivation: '',
    availability: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  // Login state
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Fetch request details on mount
  useEffect(() => {
    async function load() {
      try {
        const data = await getTeamRequest(requestId);
        setRequest(data);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to load request';
        setLoadError(message);
      } finally {
        setLoadingRequest(false);
      }
    }
    load();
  }, [requestId]);

  const isValid =
    formData.role.trim().length > 0 &&
    formData.skills.length > 0 &&
    formData.motivation.trim().length > 10 &&
    formData.availability !== '' &&
    isAuthenticated;

  const handleLogin = useCallback(async () => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const authUrl = await getAuthUrl(`/apps/team-matcher/respond/${requestId}`);
      if (!authUrl) {
        throw new Error('未获取到登录地址');
      }
      window.location.href = authUrl;
    } catch (err) {
      console.error('Failed to get auth URL:', err);
      setLoginError('无法连接后端服务，请确认后端已启动');
      setIsLoggingIn(false);
    }
  }, [requestId]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || isSubmitting || !user) return;

      setIsSubmitting(true);
      setSubmitError(null);
      try {
        await submitTeamOffer({
          request_id: requestId,
          agent_id: user.agent_id,
          agent_name: user.display_name,
          role: formData.role,
          skills: formData.skills,
          specialties: formData.skills,
          motivation: formData.motivation,
          availability: formData.availability,
        });
        setSubmitted(true);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to submit offer';
        setSubmitError(message);
        setIsSubmitting(false);
      }
    },
    [formData, isValid, isSubmitting, requestId, user]
  );

  // --- Success state ---
  if (submitted) {
    return (
      <div className="team-matcher-root">
        <TeamBackground />
        <TeamNav currentStep="progress" />
        <main className={styles.main}>
          <div className={styles.successCard}>
            <div className={styles.successIcon}>
              <i className="ri-checkbox-circle-line" />
            </div>
            <h2 className={styles.successTitle}>已提交</h2>
            <p className={styles.successDesc}>
              你的参与意向已发送，等待组队方案生成。
            </p>
            <p className={styles.successHint}>
              当收到足够响应后，系统会自动生成最佳团队组合方案。
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="progress" />
      <main className={styles.main}>
        <form className={styles.form} onSubmit={handleSubmit}>
          {/* Header */}
          <div className={styles.header}>
            <div className={styles.iconWrapper}>
              <i className="ri-hand-heart-line" />
            </div>
            <h1 className={styles.title}>响应组队请求</h1>
            <p className={styles.subtitle}>
              查看请求详情，提交你的参与意向
            </p>
          </div>

          {/* Request details card */}
          {loadingRequest && (
            <div className={styles.requestCard}>
              <div className={styles.requestSkeleton} />
              <div className={styles.requestSkeletonShort} />
            </div>
          )}
          {loadError && (
            <div className={styles.errorBanner}>
              <i className="ri-error-warning-line" />
              <span>{loadError}</span>
            </div>
          )}
          {request && (
            <div className={styles.requestCard}>
              <div className={styles.requestLabel}>
                <i className="ri-file-text-line" />
                组队请求
              </div>
              <p className={styles.requestIdea}>{request.title}</p>
              <div className={styles.requestMeta}>
                {request.required_roles.length > 0 && request.required_roles[0] !== '通用成员' && (
                  <p className={styles.requestRoles}>
                    <i className="ri-group-line" />
                    正在找: {request.required_roles.join(', ')}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Login prompt */}
          {!isChecking && !isAuthenticated && (
            <div className={styles.loginPrompt}>
              <div className={styles.loginPromptIcon}>
                <i className="ri-user-line" />
              </div>
              <div className={styles.loginPromptText}>
                <p className={styles.loginPromptTitle}>登录后才能提交响应</p>
                <p className={styles.loginPromptDesc}>
                  登录 SecondMe 以提交你的参与意向
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

          {/* Logged-in indicator */}
          {isAuthenticated && user && (
            <div className={styles.loggedInBanner}>
              <i className="ri-checkbox-circle-line" />
              <span>已登录为 {user.display_name}</span>
            </div>
          )}

          {/* Role */}
          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="offer-role">
              <i className="ri-user-star-line" />
              角色定位
            </label>
            <input
              id="offer-role"
              type="text"
              className={styles.textInput}
              placeholder="你想在团队中担任什么角色？如：前端开发、产品设计..."
              value={formData.role}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, role: e.target.value }))
              }
              maxLength={100}
            />
          </div>

          {/* Skills */}
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
              hint="选择你擅长的技能"
            />
          </div>

          {/* Motivation */}
          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="offer-motivation">
              <i className="ri-chat-heart-line" />
              参与动机
            </label>
            <textarea
              id="offer-motivation"
              className={styles.textarea}
              placeholder="为什么你想加入这个项目？你能带来什么独特的价值？"
              value={formData.motivation}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, motivation: e.target.value }))
              }
              maxLength={500}
              rows={4}
            />
            <div className={styles.charCount}>
              <span>{formData.motivation.length}</span> / 500
            </div>
          </div>

          {/* Availability */}
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
                    name="availability"
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

          {/* Submit error */}
          {submitError && (
            <div className={styles.errorBanner}>
              <i className="ri-error-warning-line" />
              <span>{submitError}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className={`${styles.submitBtn} ${isValid ? styles.submitBtnReady : ''}`}
            disabled={!isValid || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className={styles.submitSpinner} />
                提交中...
              </>
            ) : (
              <>
                <i className="ri-send-plane-line" />
                提交响应
              </>
            )}
          </button>

          <p className={styles.submitHint}>
            提交后，你的信息将参与团队组合方案的生成
          </p>
        </form>
      </main>
    </div>
  );
}
