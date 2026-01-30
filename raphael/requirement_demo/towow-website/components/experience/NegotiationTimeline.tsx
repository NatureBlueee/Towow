'use client';

import { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import styles from './NegotiationTimeline.module.css';

interface NegotiationMessage {
  message_id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  message_type: 'text' | 'system' | 'action';
  content: string;
  timestamp: string;
}

type NegotiationStatus = 'waiting' | 'in_progress' | 'completed' | 'failed';

interface NegotiationTimelineProps {
  messages: NegotiationMessage[];
  status: NegotiationStatus;
  isLoading?: boolean;
  currentUserId?: string;
}

const statusConfig = {
  waiting: { label: '等待中', color: 'var(--c-text-gray)' },
  in_progress: { label: '协商进行中', color: 'var(--c-primary)' },
  completed: { label: '协商完成', color: 'var(--c-secondary)' },
  failed: { label: '协商失败', color: '#e53935' },
};

export function NegotiationTimeline({
  messages,
  status,
  isLoading = false,
  currentUserId,
}: NegotiationTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部（平滑滚动）
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages]);

  const config = statusConfig[status];

  return (
    <div className={styles.timeline}>
      {/* 状态指示器 */}
      <div className={styles.statusBar}>
        <div
          className={styles.statusDot}
          style={{ backgroundColor: config.color }}
        />
        <span className={styles.statusLabel}>{config.label}</span>
        {status === 'in_progress' && (
          <span className={styles.statusPulse} />
        )}
      </div>

      {/* 消息列表 */}
      <div ref={containerRef} className={styles.messageList}>
        {messages.length === 0 && !isLoading && (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>💬</div>
            <p>等待协商开始...</p>
            <p className={styles.emptyHint}>提交需求后，Agent 将开始协商</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={msg.message_id}
            className={styles.messageWrapper}
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <MessageBubble
              message={msg}
              isCurrentUser={msg.sender_id === currentUserId}
              enableTypewriter={index === messages.length - 1}
            />
          </div>
        ))}

        {isLoading && (
          <div className={styles.loading}>
            <span className={styles.loadingDot} />
            <span className={styles.loadingDot} />
            <span className={styles.loadingDot} />
          </div>
        )}
      </div>
    </div>
  );
}
