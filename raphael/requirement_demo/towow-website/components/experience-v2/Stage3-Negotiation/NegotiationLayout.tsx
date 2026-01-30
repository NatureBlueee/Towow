'use client';

import { useState, useEffect, useRef } from 'react';
import { Agent, EventCard, EventCardType } from '../shared/types';
import styles from './Stage3.module.css';

interface NegotiationLayoutProps {
  agents: Agent[];
  events: EventCard[];
  isPlaying: boolean;
  onTogglePlay: () => void;
  onSpeedUp: () => void;
  onSkipToResult: () => void;
  activeConnections?: { from: string; to: string }[];
}

// Event card icon mapping
const EVENT_ICONS: Record<EventCardType, { icon: string; color: string }> = {
  insight: { icon: 'lightbulb', color: '#8B5CF6' },
  transform: { icon: 'refresh', color: '#F59E0B' },
  combine: { icon: 'link', color: '#10B981' },
  confirm: { icon: 'check', color: '#3B82F6' },
};

const EVENT_LABELS: Record<EventCardType, string> = {
  insight: '洞察',
  transform: '转变',
  combine: '组合',
  confirm: '确认',
};

export function NegotiationLayout({
  agents,
  events,
  isPlaying,
  onTogglePlay,
  onSpeedUp,
  onSkipToResult,
  activeConnections = [],
}: NegotiationLayoutProps) {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest event
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  // Calculate mini network positions
  const nodePositions = agents.map((_, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / agents.length;
    const radius = 60;
    return {
      x: 80 + Math.cos(angle) * radius,
      y: 80 + Math.sin(angle) * radius,
    };
  });

  return (
    <div className={styles.container}>
      <div className={styles.layout}>
        {/* Left: Dynamic Network Graph */}
        <div className={styles.networkPanel}>
          <h3 className={styles.panelTitle}>协商网络</h3>
          <div className={styles.miniNetwork}>
            <svg className={styles.miniSvg} viewBox="0 0 160 160">
              {/* Connection lines */}
              {agents.map((agent, i) => {
                const pos = nodePositions[i];
                const isActive = activeConnections.some(
                  (c) => c.from === agent.id || c.to === agent.id
                );
                return (
                  <line
                    key={`line-${agent.id}`}
                    x1="80"
                    y1="80"
                    x2={pos.x}
                    y2={pos.y}
                    className={`${styles.miniLine} ${
                      isActive ? styles.miniLineActive : ''
                    }`}
                  />
                );
              })}

              {/* Agent-to-agent connections */}
              {activeConnections.map((conn, idx) => {
                const fromIdx = agents.findIndex((a) => a.id === conn.from);
                const toIdx = agents.findIndex((a) => a.id === conn.to);
                if (fromIdx === -1 || toIdx === -1) return null;
                const fromPos = nodePositions[fromIdx];
                const toPos = nodePositions[toIdx];
                return (
                  <line
                    key={`conn-${idx}`}
                    x1={fromPos.x}
                    y1={fromPos.y}
                    x2={toPos.x}
                    y2={toPos.y}
                    className={styles.activeConnection}
                  />
                );
              })}

              {/* Center node */}
              <circle cx="80" cy="80" r="12" className={styles.miniCenter} />

              {/* Agent nodes */}
              {agents.map((agent, i) => {
                const pos = nodePositions[i];
                const isActive = activeConnections.some(
                  (c) => c.from === agent.id || c.to === agent.id
                );
                return (
                  <g key={agent.id}>
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r="10"
                      className={`${styles.miniNode} ${
                        isActive ? styles.miniNodeActive : ''
                      }`}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 4}
                      className={styles.miniNodeText}
                    >
                      {agent.name.charAt(0)}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Agent list */}
          <div className={styles.agentList}>
            {agents.map((agent) => {
              const isActive = activeConnections.some(
                (c) => c.from === agent.id || c.to === agent.id
              );
              return (
                <div
                  key={agent.id}
                  className={`${styles.agentItem} ${
                    isActive ? styles.agentItemActive : ''
                  }`}
                >
                  <div className={styles.agentDot} />
                  <span className={styles.agentItemName}>{agent.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Event Card Stream */}
        <div className={styles.eventsPanel}>
          <h3 className={styles.panelTitle}>关键事件</h3>
          <div className={styles.eventStream}>
            {events.map((event) => {
              // Defensive check for undefined event or type
              if (!event || !event.type) return null;
              const config = EVENT_ICONS[event.type];
              if (!config) return null;
              const isExpanded = expandedCard === event.id;

              return (
                <div
                  key={event.id}
                  className={`${styles.eventCard} ${
                    isExpanded ? styles.eventCardExpanded : ''
                  }`}
                  style={{ '--card-color': config.color } as React.CSSProperties}
                  onClick={() =>
                    setExpandedCard(isExpanded ? null : event.id)
                  }
                >
                  <div className={styles.eventHeader}>
                    <div
                      className={styles.eventIcon}
                      style={{ background: `${config.color}20` }}
                    >
                      <EventIcon type={event.type} color={config.color} />
                    </div>
                    <div className={styles.eventMeta}>
                      <span
                        className={styles.eventType}
                        style={{ color: config.color }}
                      >
                        {EVENT_LABELS[event.type]}
                      </span>
                      <span className={styles.eventTitle}>{event.title}</span>
                    </div>
                    <svg
                      className={`${styles.expandIcon} ${
                        isExpanded ? styles.expandIconRotated : ''
                      }`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>

                  {isExpanded && (
                    <div className={styles.eventContent}>
                      <p>{event.content}</p>
                      {event.agents && event.agents.length > 0 && (
                        <div className={styles.eventAgents}>
                          <span className={styles.eventAgentsLabel}>
                            参与者:
                          </span>
                          {event.agents.map((agentId) => {
                            const agent = agents.find((a) => a.id === agentId);
                            return agent ? (
                              <span
                                key={agentId}
                                className={styles.eventAgentTag}
                              >
                                {agent.name}
                              </span>
                            ) : null;
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={eventsEndRef} />
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        <button
          className={styles.controlButton}
          onClick={onSpeedUp}
          aria-label="加速"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polygon points="5 4 15 12 5 20 5 4" />
            <polygon points="13 4 23 12 13 20 13 4" />
          </svg>
          <span>加速</span>
        </button>

        <button
          className={`${styles.controlButton} ${styles.controlButtonPrimary}`}
          onClick={onTogglePlay}
          aria-label={isPlaying ? '暂停' : '继续'}
        >
          {isPlaying ? (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          )}
          <span>{isPlaying ? '暂停' : '继续'}</span>
        </button>

        <button
          className={styles.controlButton}
          onClick={onSkipToResult}
          aria-label="跳到结果"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polygon points="5 4 15 12 5 20 5 4" />
            <line x1="19" y1="5" x2="19" y2="19" />
          </svg>
          <span>跳到结果</span>
        </button>
      </div>
    </div>
  );
}

// Event Icon Component
function EventIcon({ type, color }: { type: EventCardType; color: string }) {
  switch (type) {
    case 'insight':
      return (
        <svg
          width="16"
          height="16"
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
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
      );
    case 'combine':
      return (
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
      );
    case 'confirm':
      return (
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
        >
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      );
  }
}
