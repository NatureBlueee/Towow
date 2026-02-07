'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { useTeamAuth } from '@/context/TeamAuthContext';
import { getAuthUrl } from '@/lib/api/auth';
import { getTeamRequests } from '@/lib/team-matcher/api';
import type { TeamRequestListItem } from '@/lib/team-matcher/types';
import styles from './BrowsePage.module.css';

export function BrowsePageClient() {
  const router = useRouter();
  const { user, isChecking, isAuthenticated } = useTeamAuth();

  const [requests, setRequests] = useState<TeamRequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Fetch requests on mount
  useEffect(() => {
    let cancelled = false;

    async function fetchRequests() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getTeamRequests();
        if (!cancelled) {
          setRequests(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '无法加载请求列表');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchRequests();
    return () => { cancelled = true; };
  }, []);

  const handleLogin = useCallback(async () => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const authUrl = await getAuthUrl('/apps/team-matcher/browse');
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

  const handleRetry = useCallback(() => {
    setIsLoading(true);
    setError(null);
    getTeamRequests()
      .then(setRequests)
      .catch((err) => setError(err instanceof Error ? err.message : '无法加载请求列表'))
      .finally(() => setIsLoading(false));
  }, []);

  const formatTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return '刚刚';
      if (diffMin < 60) return `${diffMin} 分钟前`;
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) return `${diffHours} 小时前`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays} 天前`;
    } catch {
      return '';
    }
  };

  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="browse" />
      <main className={styles.main}>
        <div className={styles.container}>
          {/* Header */}
          <div className={styles.header}>
            <div className={styles.iconWrapper}>
              <i className="ri-radar-line" />
            </div>
            <h1 className={styles.title}>浏览组队请求</h1>
            <p className={styles.subtitle}>
              发现正在寻找伙伴的项目，响应感兴趣的请求
            </p>
          </div>

          {/* Login prompt */}
          {!isChecking && !isAuthenticated && (
            <div className={styles.loginPrompt}>
              <div className={styles.loginPromptIcon}>
                <i className="ri-user-line" />
              </div>
              <div className={styles.loginPromptText}>
                <p className={styles.loginPromptTitle}>登录以响应请求</p>
                <p className={styles.loginPromptDesc}>
                  登录后可以向感兴趣的项目提交你的参与意向
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
                    <span className={styles.spinner} />
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

          {/* Loading state */}
          {isLoading && (
            <div className={styles.loading}>
              <div className={styles.spinner} />
              <p>加载请求列表...</p>
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <div className={styles.error}>
              <i className="ri-error-warning-line" />
              <p>{error}</p>
              <button className={styles.retryBtn} onClick={handleRetry}>
                <i className="ri-refresh-line" />
                重试
              </button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && requests.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>
                <i className="ri-inbox-line" />
              </div>
              <h2 className={styles.emptyTitle}>暂无组队请求</h2>
              <p className={styles.emptyDesc}>
                还没有人发出信号，你可以成为第一个！
              </p>
              <button
                className={styles.createBtn}
                onClick={() => router.push('/apps/team-matcher/request')}
              >
                <i className="ri-signal-tower-line" />
                发出信号
              </button>
            </div>
          )}

          {/* Request cards */}
          {!isLoading && !error && requests.length > 0 && (
            <div className={styles.cardList}>
              {requests.map((req, index) => (
                <div
                  key={req.request_id}
                  className={styles.card}
                  style={{ animationDelay: `${index * 80}ms` }}
                >
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>{req.title}</h3>
                    <div className={styles.offerBadge}>
                      <i className="ri-user-voice-line" />
                      {req.offer_count} 人响应
                    </div>
                  </div>

                  <p className={styles.cardDescription}>{req.description}</p>

                  {req.required_roles.length > 0 && (
                    <div className={styles.cardMeta}>
                      {req.required_roles.map((role) => (
                        <span key={role} className={styles.roleTag}>
                          <i className="ri-user-star-line" />
                          {role}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className={styles.cardFooter}>
                    <span className={styles.cardTime}>
                      {formatTime(req.created_at)}
                    </span>
                    <button
                      className={styles.respondBtn}
                      onClick={() =>
                        router.push(`/apps/team-matcher/respond/${req.request_id}`)
                      }
                    >
                      <i className="ri-hand-heart-line" />
                      响应这个请求
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
