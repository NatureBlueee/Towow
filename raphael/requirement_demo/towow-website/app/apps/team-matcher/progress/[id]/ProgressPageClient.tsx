'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import '@/styles/team-matcher.css';
import { TeamBackground } from '@/components/team-matcher/TeamBackground';
import { TeamNav } from '@/components/team-matcher/TeamNav';
import { SignalVisualization } from '@/components/team-matcher/SignalVisualization';
import { useTeamMatching } from '@/hooks/useTeamMatching';
import type { ProgressStage } from '@/lib/team-matcher/types';
import styles from './ProgressPage.module.css';

interface ProgressPageClientProps {
  requestId: string;
}

/**
 * Real-time progress page that shows:
 * 1. Signal animation + stage indicator
 * 2. Request details card (what you submitted)
 * 3. Share link for teammates to respond
 * 4. Offer counter (X / Y)
 * 5. Activity log (real-time events)
 */
export function ProgressPageClient({ requestId }: ProgressPageClientProps) {
  const router = useRouter();
  const teamMatching = useTeamMatching();
  const [copied, setCopied] = useState(false);

  // Resume the request on mount
  const hasInitializedRef = useRef(false);
  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;
    teamMatching.resumeRequest(requestId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  // Map hook status to ProgressStage
  const mapStatusToStage = (hookStatus: string): ProgressStage => {
    switch (hookStatus) {
      case 'broadcasting':
      case 'submitting':
      case 'idle':
        return 'broadcasting';
      case 'receiving':
        return 'receiving';
      case 'generating':
        return 'generating';
      case 'complete':
        return 'complete';
      default:
        return 'broadcasting';
    }
  };

  const stage = mapStatusToStage(teamMatching.status);
  const hasError = teamMatching.status === 'error';
  const detail = teamMatching.requestDetail;

  // Build the share link for teammates
  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/apps/team-matcher/respond/${requestId}`
    : '';

  const handleCopyLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text in a temporary input
      const input = document.createElement('input');
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [shareUrl]);

  // Navigate to proposals when complete
  const handleViewProposals = useCallback(() => {
    router.push(`/apps/team-matcher/proposals/${requestId}`);
  }, [router, requestId]);

  // Retry on error
  const handleRetry = useCallback(() => {
    teamMatching.reset();
    router.push('/apps/team-matcher/request');
  }, [teamMatching, router]);

  // Extract metadata for display
  const frontendSchema = detail?.metadata?.frontend_schema as
    | { project_idea?: string; skills?: string[]; availability?: string }
    | undefined;

  return (
    <div className="team-matcher-root">
      <TeamBackground />
      <TeamNav currentStep="progress" />
      <main className={styles.main}>
        {/* Signal animation + stage */}
        <SignalVisualization
          stage={stage}
          offersCount={
            detail?.offer_count ?? teamMatching.offers.length
          }
          offerSummaries={teamMatching.offers}
        />

        {/* Offer counter (below animation, above details) */}
        {!hasError && detail && stage !== 'complete' && (
          <div className={styles.offerCounter}>
            <span className={styles.offerCountCurrent}>
              {detail.offer_count ?? teamMatching.offers.length}
            </span>
            <span className={styles.offerCountSeparator}>/</span>
            <span className={styles.offerCountTarget}>{detail.team_size}</span>
            <span className={styles.offerCountLabel}>位伙伴已响应</span>
          </div>
        )}

        {/* Two-column layout for details + share */}
        <div className={styles.infoGrid}>
          {/* Request details card */}
          {detail && (
            <div className={styles.detailCard}>
              <div className={styles.detailCardHeader}>
                <i className="ri-file-text-line" />
                <span>你的请求</span>
              </div>
              <h3 className={styles.detailTitle}>{detail.title}</h3>
              {frontendSchema?.project_idea && (
                <p className={styles.detailDesc}>{frontendSchema.project_idea}</p>
              )}
              <div className={styles.detailMeta}>
                {frontendSchema?.skills && frontendSchema.skills.length > 0 && (
                  <div className={styles.detailMetaRow}>
                    <i className="ri-tools-line" />
                    <div className={styles.detailTags}>
                      {frontendSchema.skills.map((s) => (
                        <span key={s} className={styles.detailTag}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {detail.required_roles.length > 0 && detail.required_roles[0] !== '通用成员' && (
                  <div className={styles.detailMetaRow}>
                    <i className="ri-group-line" />
                    <div className={styles.detailTags}>
                      {detail.required_roles.map((r) => (
                        <span key={r} className={styles.detailTag}>{r}</span>
                      ))}
                    </div>
                  </div>
                )}
                {frontendSchema?.availability && (
                  <div className={styles.detailMetaRow}>
                    <i className="ri-time-line" />
                    <span className={styles.detailMetaText}>
                      {frontendSchema.availability}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Share / invite card */}
          {stage !== 'complete' && (
            <div className={styles.shareCard}>
              <div className={styles.shareCardHeader}>
                <i className="ri-share-forward-line" />
                <span>邀请队友响应</span>
              </div>
              <p className={styles.shareDesc}>
                把下面的链接发给你的队友，让他们提交参与意向
              </p>
              <div className={styles.shareUrlBox}>
                <code className={styles.shareUrl}>
                  {shareUrl || `.../${requestId}`}
                </code>
                <button
                  className={styles.copyBtn}
                  onClick={handleCopyLink}
                  title="复制链接"
                >
                  {copied ? (
                    <><i className="ri-check-line" /> 已复制</>
                  ) : (
                    <><i className="ri-file-copy-line" /> 复制</>
                  )}
                </button>
              </div>
              <p className={styles.shareHint}>
                当收到 {detail?.team_size ?? 3} 个响应后，系统将自动生成团队方案
              </p>
            </div>
          )}
        </div>

        {/* LLM Progress: show streaming text during generating stage */}
        {stage === 'generating' && teamMatching.llmProgress && (
          <div className={styles.llmProgress}>
            <div className={styles.llmProgressHeader}>
              <i className="ri-sparkling-line" />
              <span>AI 正在组合最佳团队方案...</span>
            </div>
            <div className={styles.llmProgressContent}>
              {teamMatching.llmProgress}
              <span className={styles.llmCursor} />
            </div>
          </div>
        )}

        {/* Activity log */}
        {teamMatching.activityLog.length > 0 && (
          <div className={styles.activityLog}>
            <div className={styles.activityLogHeader}>
              <i className="ri-list-check-2" />
              <span>活动日志</span>
            </div>
            <div className={styles.activityLogList}>
              {teamMatching.activityLog.map((entry, i) => (
                <div
                  key={i}
                  className={`${styles.activityLogEntry} ${styles[`log_${entry.type}`] || ''}`}
                >
                  <span className={styles.activityLogTime}>{entry.time}</span>
                  <span className={styles.activityLogMsg}>{entry.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error state */}
        {hasError && teamMatching.error && (
          <div className={styles.errorPanel}>
            <i className="ri-error-warning-line" />
            <p>{teamMatching.error}</p>
            <button className={styles.retryBtn} onClick={handleRetry}>
              <i className="ri-refresh-line" />
              重新开始
            </button>
          </div>
        )}

        {/* WebSocket status indicator — always visible */}
        <div className={`${styles.wsStatus} ${
          teamMatching.wsStatus === 'connected' ? styles.wsConnected :
          teamMatching.wsStatus === 'error' ? styles.wsError : ''
        }`}>
          {teamMatching.wsStatus === 'connected' && (
            <><i className="ri-wifi-line" /> 实时连接已建立</>
          )}
          {teamMatching.wsStatus === 'connecting' && (
            <><i className="ri-loader-4-line" /> 正在连接服务器...</>
          )}
          {teamMatching.wsStatus === 'reconnecting' && (
            <><i className="ri-refresh-line" /> 正在重新连接...</>
          )}
          {teamMatching.wsStatus === 'error' && (
            <><i className="ri-wifi-off-line" /> 连接失败，使用轮询模式</>
          )}
          {teamMatching.wsStatus === 'disconnected' && (
            <><i className="ri-wifi-off-line" /> 未连接</>
          )}
        </div>

        {/* View proposals button */}
        {stage === 'complete' && (
          <button
            className={styles.viewBtn}
            onClick={handleViewProposals}
          >
            <i className="ri-team-line" />
            查看团队方案
            <i className="ri-arrow-right-line" />
          </button>
        )}
      </main>
    </div>
  );
}
