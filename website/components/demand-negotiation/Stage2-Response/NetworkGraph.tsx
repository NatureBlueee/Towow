'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Agent } from '../shared/types';
import styles from './Stage2.module.css';

interface NetworkGraphProps {
  requirement: string;
  agents: Agent[];
  onStartNegotiation: () => void;
  isAnimating?: boolean;
}

type Phase = 'idle' | 'broadcasting' | 'waiting' | 'responding' | 'complete';

// Calculate node positions in a circle around center
function calculateNodePositions(count: number, radius: number) {
  const positions: { x: number; y: number }[] = [];
  const startAngle = -Math.PI / 2; // Start from top

  for (let i = 0; i < count; i++) {
    const angle = startAngle + (2 * Math.PI * i) / count;
    positions.push({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  }

  return positions;
}

// Phase label keys — resolved at render time
const PHASE_LABEL_KEYS: Record<Phase, string> = {
  idle: '',
  broadcasting: 'broadcastingPhase',
  waiting: 'waitingPhase',
  responding: 'respondingPhase',
  complete: 'completePhase',
};

export function NetworkGraph({
  requirement,
  agents,
  onStartNegotiation,
  isAnimating = true,
}: NetworkGraphProps) {
  const t = useTranslations('DemandNegotiation.network');
  const [phase, setPhase] = useState<Phase>('idle');
  const [visibleAgents, setVisibleAgents] = useState<number>(0);
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);
  const [showingResponse, setShowingResponse] = useState<string | null>(null);
  const [broadcastWaveKey, setBroadcastWaveKey] = useState(0);

  // Calculate positions
  const nodePositions = useMemo(
    () => calculateNodePositions(agents.length, 140),
    [agents.length]
  );

  // Animation sequence
  useEffect(() => {
    if (!isAnimating) {
      setPhase('complete');
      setVisibleAgents(agents.length);
      return;
    }

    // Reset state
    setPhase('idle');
    setVisibleAgents(0);
    setBroadcastWaveKey((k) => k + 1);

    // Phase 1: Start broadcasting (0ms)
    const t1 = setTimeout(() => {
      setPhase('broadcasting');
    }, 100);

    // Phase 2: Waiting for responses (1.2s)
    const t2 = setTimeout(() => {
      setPhase('waiting');
    }, 1200);

    // Phase 3: Agents start responding (1.8s)
    const t3 = setTimeout(() => {
      setPhase('responding');

      // Agents appear with staggered timing
      let count = 0;
      const interval = setInterval(() => {
        count++;
        if (count > agents.length) {
          clearInterval(interval);
          setPhase('complete');
          return;
        }
        setVisibleAgents(count);
      }, 400); // Faster appearance

      return () => clearInterval(interval);
    }, 1800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [agents.length, isAnimating]);

  // Show initial responses briefly when agent appears
  useEffect(() => {
    if (visibleAgents > 0 && visibleAgents <= agents.length) {
      const agent = agents[visibleAgents - 1];
      if (agent.initialResponse) {
        setShowingResponse(agent.id);
        const timer = setTimeout(() => {
          setShowingResponse(null);
        }, 2000);
        return () => clearTimeout(timer);
      }
    }
  }, [visibleAgents, agents]);

  const allAgentsVisible = visibleAgents >= agents.length;
  const showBroadcast = phase === 'broadcasting' || phase === 'waiting';

  return (
    <div className={styles.container}>
      {/* Requirement summary */}
      <div className={styles.requirementBadge}>
        <span className={styles.requirementLabel}>{t('yourRequirement')}</span>
        <p className={styles.requirementText}>{requirement}</p>
      </div>

      {/* Phase indicator */}
      <div className={`${styles.phaseIndicator} ${phase !== 'idle' ? styles.phaseIndicatorVisible : ''}`}>
        {phase === 'responding' && visibleAgents > 0 ? (
          <span className={styles.phaseText}>
            {t('agentsResponding', { count: visibleAgents })}
          </span>
        ) : (
          <span className={styles.phaseText}>{PHASE_LABEL_KEYS[phase] ? t(PHASE_LABEL_KEYS[phase]) : ''}</span>
        )}
      </div>

      {/* Network visualization */}
      <div className={styles.networkContainer}>
        <svg className={styles.connectionsSvg} viewBox="-200 -200 400 400">
          {/* Broadcast waves - expanding circles */}
          {showBroadcast && (
            <g key={broadcastWaveKey}>
              {[0, 1, 2, 3].map((i) => (
                <circle
                  key={i}
                  cx="0"
                  cy="0"
                  r="40"
                  className={styles.broadcastWave}
                  style={{ animationDelay: `${i * 0.25}s` }}
                />
              ))}
            </g>
          )}

          {/* Agent placeholder positions (faded circles showing where agents will appear) */}
          {phase === 'waiting' &&
            agents.map((agent, index) => {
              const pos = nodePositions[index];
              return (
                <circle
                  key={`placeholder-${agent.id}`}
                  cx={pos.x}
                  cy={pos.y}
                  r="20"
                  className={styles.agentPlaceholder}
                  style={{ animationDelay: `${index * 0.1}s` }}
                />
              );
            })}

          {/* Response lines - from Agent TO center */}
          {agents.slice(0, visibleAgents).map((agent, index) => {
            const pos = nodePositions[index];
            return (
              <g key={`line-${agent.id}`}>
                {/* Connection line */}
                <line
                  x1={pos.x}
                  y1={pos.y}
                  x2="0"
                  y2="0"
                  className={styles.connectionLine}
                />
                {/* Animated pulse flowing toward center */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="5"
                  className={styles.responsePulse}
                  style={{
                    '--target-x': `${-pos.x}px`,
                    '--target-y': `${-pos.y}px`,
                  } as React.CSSProperties}
                />
              </g>
            );
          })}
        </svg>

        {/* Center node (requirement) */}
        <div
          className={`${styles.centerNode} ${
            showBroadcast ? styles.centerNodeBroadcasting : ''
          } ${visibleAgents > 0 ? styles.centerNodeReceiving : ''}`}
        >
          <div className={styles.centerNodeInner}>
            {showBroadcast ? (
              // Broadcasting icon (wifi signal)
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12.55a11 11 0 0 1 14.08 0" />
                <path d="M1.42 9a16 16 0 0 1 21.16 0" />
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                <circle cx="12" cy="20" r="1.5" fill="currentColor" />
              </svg>
            ) : (
              // Default icon
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
            )}
          </div>
          <span className={styles.centerLabel}>
            {showBroadcast ? t('broadcasting') : t('demand')}
          </span>
        </div>

        {/* Agent nodes */}
        {agents.slice(0, visibleAgents).map((agent, index) => {
          const pos = nodePositions[index];
          const isShowingResponse = showingResponse === agent.id;
          const isLatest = index === visibleAgents - 1;

          return (
            <div
              key={agent.id}
              className={`${styles.agentNodeWrapper} ${isLatest ? styles.agentNodeLatest : ''}`}
              style={{
                transform: `translate(${pos.x}px, ${pos.y}px)`,
              }}
              onMouseEnter={() => setActiveTooltip(agent.id)}
              onMouseLeave={() => setActiveTooltip(null)}
            >
              <div className={styles.agentNode}>
                {agent.avatar ? (
                  <img src={agent.avatar} alt={agent.name} className={styles.agentAvatar} />
                ) : (
                  <span className={styles.agentInitial}>{agent.name.charAt(0)}</span>
                )}
              </div>
              <span className={styles.agentName}>{agent.name}</span>

              {/* Initial response bubble */}
              {isShowingResponse && agent.initialResponse && (
                <div className={styles.responseBubble}>
                  <span className={styles.responseBubbleText}>{agent.initialResponse}</span>
                </div>
              )}

              {/* Tooltip on hover */}
              {activeTooltip === agent.id && !isShowingResponse && (
                <div className={styles.tooltip}>
                  <div className={styles.tooltipHeader}>
                    <span className={styles.tooltipName}>{agent.name}</span>
                    <span className={styles.tooltipRole}>{agent.role}</span>
                  </div>
                  <p className={styles.tooltipDesc}>{agent.description}</p>
                  <div className={styles.tooltipSkills}>
                    {agent.skills.slice(0, 3).map((skill) => (
                      <span key={skill} className={styles.skillTag}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom action area */}
      <div className={`${styles.actionArea} ${allAgentsVisible ? styles.actionAreaVisible : ''}`}>
        <p className={styles.responseCount}>
          <span className={styles.countNumber}>{agents.length}</span>
          {t('agentsResponded')}
        </p>
        <button
          className={styles.startButton}
          onClick={onStartNegotiation}
          disabled={!allAgentsVisible}
        >
          {t('startNegotiation')}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  );
}
