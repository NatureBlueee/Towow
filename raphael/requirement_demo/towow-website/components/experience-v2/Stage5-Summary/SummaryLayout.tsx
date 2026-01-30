'use client';

import { KeyInsight, TimelineEvent, STAGES } from '../shared/types';
import styles from './Stage5.module.css';

interface SummaryLayoutProps {
  timeline: TimelineEvent[];
  insights: KeyInsight[];
  onRestart: () => void;
  onShare: () => void;
  onLearnMore: () => void;
}

const INSIGHT_CONFIG = {
  insight: {
    icon: 'lightbulb',
    color: '#8B5CF6',
    label: '关键洞察',
  },
  transform: {
    icon: 'refresh',
    color: '#F59E0B',
    label: '认知转变',
  },
  discovery: {
    icon: 'sparkles',
    color: '#10B981',
    label: '意外发现',
  },
};

export function SummaryLayout({
  timeline,
  insights,
  onRestart,
  onShare,
  onLearnMore,
}: SummaryLayoutProps) {
  return (
    <div className={styles.container}>
      <h2 className={styles.title}>协商汇总</h2>

      {/* Timeline */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>协商时间线</h3>
        <div className={styles.timeline}>
          {STAGES.map((stage, index) => {
            const event = timeline.find((e) => e.stage === stage.id);
            const isCompleted = !!event;

            return (
              <div key={stage.id} className={styles.timelineItem}>
                {index > 0 && (
                  <div
                    className={`${styles.timelineConnector} ${
                      isCompleted ? styles.timelineConnectorActive : ''
                    }`}
                  />
                )}
                <div
                  className={`${styles.timelineNode} ${
                    isCompleted ? styles.timelineNodeActive : ''
                  }`}
                >
                  {isCompleted ? (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <div className={styles.timelineContent}>
                  <span className={styles.timelineLabel}>{stage.label}</span>
                  {event && (
                    <span className={styles.timelineTime}>
                      {formatTime(event.timestamp)}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Key Insights */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>关键发现</h3>
        <div className={styles.insightGrid}>
          {insights.map((insight, index) => {
            const config = INSIGHT_CONFIG[insight.type];
            return (
              <div
                key={index}
                className={styles.insightCard}
                style={{ '--card-color': config.color } as React.CSSProperties}
              >
                <div
                  className={styles.insightIcon}
                  style={{ background: `${config.color}15` }}
                >
                  <InsightIcon type={insight.type} color={config.color} />
                </div>
                <div className={styles.insightContent}>
                  <span
                    className={styles.insightType}
                    style={{ color: config.color }}
                  >
                    {config.label}
                  </span>
                  <h4 className={styles.insightTitle}>{insight.title}</h4>
                  <p className={styles.insightText}>{insight.content}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Value Summary */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>价值总结</h3>
        <div className={styles.valueGrid}>
          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </div>
            <span className={styles.valueLabel}>成本优化</span>
            <span className={styles.valueNumber}>-84%</span>
          </div>
          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <span className={styles.valueLabel}>时间节省</span>
            <span className={styles.valueNumber}>3个月</span>
          </div>
          <div className={styles.valueCard}>
            <div className={styles.valueIcon}>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <span className={styles.valueLabel}>协作方</span>
            <span className={styles.valueNumber}>4个</span>
          </div>
        </div>
      </section>

      {/* Actions */}
      <div className={styles.actions}>
        <button className={styles.actionButton} onClick={onRestart}>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          重新开始
        </button>
        <button
          className={`${styles.actionButton} ${styles.actionButtonPrimary}`}
          onClick={onShare}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          分享案例
        </button>
        <button className={styles.actionButton} onClick={onLearnMore}>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />
          </svg>
          了解更多
        </button>
      </div>
    </div>
  );
}

function InsightIcon({
  type,
  color,
}: {
  type: KeyInsight['type'];
  color: string;
}) {
  switch (type) {
    case 'insight':
      return (
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <path d="M9 18h6M10 22h4M12 2v1M4.22 4.22l.71.71M1 12h1M4.22 19.78l.71-.71M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z" />
        </svg>
      );
    case 'transform':
      return (
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
      );
    case 'discovery':
      return (
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      );
  }
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}
