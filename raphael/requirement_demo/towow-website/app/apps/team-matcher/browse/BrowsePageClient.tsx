'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
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
  const t = useTranslations('TeamMatcher.browse');
  const tForm = useTranslations('TeamMatcher.form');
  const tCommon = useTranslations('Common');
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
          setError(err instanceof Error ? err.message : t('loadError'));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchRequests();
    return () => { cancelled = true; };
  }, [t]);

  const handleLogin = useCallback(async () => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const authUrl = await getAuthUrl('/apps/team-matcher/browse');
      if (!authUrl) {
        throw new Error(tForm('loginErrorAuth'));
      }
      window.location.href = authUrl;
    } catch (err) {
      console.error('Failed to get auth URL:', err);
      setLoginError(tForm('loginErrorBackend'));
      setIsLoggingIn(false);
    }
  }, [tForm]);

  const handleRetry = useCallback(() => {
    setIsLoading(true);
    setError(null);
    getTeamRequests()
      .then(setRequests)
      .catch((err) => setError(err instanceof Error ? err.message : t('loadError')))
      .finally(() => setIsLoading(false));
  }, [t]);

  const formatTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return t('justNow');
      if (diffMin < 60) return t('minutesAgo', { count: diffMin });
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) return t('hoursAgo', { count: diffHours });
      const diffDays = Math.floor(diffHours / 24);
      return t('daysAgo', { count: diffDays });
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
            <h1 className={styles.title}>{t('title')}</h1>
            <p className={styles.subtitle}>{t('subtitle')}</p>
          </div>

          {/* Login prompt */}
          {!isChecking && !isAuthenticated && (
            <div className={styles.loginPrompt}>
              <div className={styles.loginPromptIcon}>
                <i className="ri-user-line" />
              </div>
              <div className={styles.loginPromptText}>
                <p className={styles.loginPromptTitle}>{t('loginPromptTitle')}</p>
                <p className={styles.loginPromptDesc}>{t('loginPromptDesc')}</p>
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
                    {tForm('redirecting')}
                  </>
                ) : (
                  <>
                    <i className="ri-login-box-line" />
                    {tForm('loginSecondMe')}
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
              <p>{t('loadingRequests')}</p>
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <div className={styles.error}>
              <i className="ri-error-warning-line" />
              <p>{error}</p>
              <button className={styles.retryBtn} onClick={handleRetry}>
                <i className="ri-refresh-line" />
                {tCommon('retry')}
              </button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && requests.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>
                <i className="ri-inbox-line" />
              </div>
              <h2 className={styles.emptyTitle}>{t('emptyTitle')}</h2>
              <p className={styles.emptyDesc}>{t('emptyDesc')}</p>
              <button
                className={styles.createBtn}
                onClick={() => router.push('/apps/team-matcher/request')}
              >
                <i className="ri-signal-tower-line" />
                {t('sendSignal')}
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
                      {t('responseCount', { count: req.offer_count })}
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
                      {t('respondToRequest')}
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
