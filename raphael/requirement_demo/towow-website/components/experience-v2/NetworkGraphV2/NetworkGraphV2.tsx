'use client';

import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Agent, NetworkPhase, AgentStatus, AgentWithStatus, ResponseType } from '../shared/types';
import styles from './NetworkGraphV2.module.css';

interface NetworkGraphV2Props {
  requirement: string;
  agents: Agent[];
  onComplete: () => void;
  onStartNegotiation?: () => void;
}

// Placeholder circle positions (scattered around the canvas)
const PLACEHOLDER_POSITIONS = Array.from({ length: 25 }, (_, i) => {
  const angle = (i / 25) * Math.PI * 2 + Math.random() * 0.5;
  const radius = 100 + Math.random() * 120;
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
    size: 15 + Math.random() * 10,
  };
});

// Calculate circle positions for converged agents
function calculateCirclePositions(count: number, radius: number) {
  const positions: { x: number; y: number }[] = [];
  const startAngle = -Math.PI / 2;
  for (let i = 0; i < count; i++) {
    const angle = startAngle + (2 * Math.PI * i) / count;
    positions.push({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  }
  return positions;
}

// Phase timing configuration (in ms) - 放慢动画速度
const PHASE_TIMING = {
  launch: 1500,      // 需求发射动画
  broadcast: 4000,   // 广播扫描（多波）
  scan: 3000,        // 发现 Agent（每个 400ms）
  classify: 2000,    // 分类动画
  converge: 2500,    // 汇聚动画
  respond: 0,        // 用户控制
  negotiate: 4000,   // 信息汇聚
  filter: 2000,      // 筛选动画
  deep: 5000,        // 深入协商
  proposal: 0,       // 用户控制
};

export function NetworkGraphV2({
  requirement,
  agents,
  onComplete,
  onStartNegotiation,
}: NetworkGraphV2Props) {
  // Phase state
  const [phase, setPhase] = useState<NetworkPhase>('idle');
  const [waveCount, setWaveCount] = useState(0);
  const [discoveredAgents, setDiscoveredAgents] = useState<number[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showingResponse, setShowingResponse] = useState<string | null>(null);
  const [activeConnections, setActiveConnections] = useState<{ from: string; to: string }[]>([]);
  const [filteredAgents, setFilteredAgents] = useState<string[]>([]);
  const [peerChat, setPeerChat] = useState<{ agent1: string; agent2: string } | null>(null);

  // Refs for animation control
  const containerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useRef(false);

  // Check for reduced motion preference
  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  // Assign statuses to agents
  const agentsWithStatus: AgentWithStatus[] = useMemo(() => {
    // Predefined statuses for demo
    const statusMap: Record<string, AgentStatus> = {
      'alex': 'willing',
      'xiaolin': 'willing',
      'studio': 'notMatch',
      'cursor': 'willing',
      'laowang': 'willing',
      'notion': 'willing',
      'bubble': 'observing',
    };

    // Predefined responses
    const responseMap: Record<string, { type: ResponseType; title: string; content: string; conditions?: string[]; price?: number }> = {
      'alex': {
        type: 'offer',
        title: '技术指导服务',
        content: '我可以提供每周2小时的技术指导，帮你解决开发中的难题。',
        conditions: ['远程协作', '按月付费'],
        price: 2000,
      },
      'xiaolin': {
        type: 'competition',
        title: '后端开发竞标',
        content: '我想竞争这个项目的后端开发部分，可以提供完整的API设计和数据库架构。',
        conditions: ['需要明确需求文档', '3周交付'],
        price: 8000,
      },
      'cursor': {
        type: 'suggestion',
        title: 'AI辅助开发建议',
        content: '你这个需求可以用AI辅助开发来加速，我可以帮你提升3倍开发效率。',
        price: 200,
      },
      'laowang': {
        type: 'suggestion',
        title: '需求重构建议',
        content: '先聊聊你真正想解决什么问题？也许你不需要技术合伙人，而是需要快速验证想法的能力。',
        price: 500,
      },
      'notion': {
        type: 'offer',
        title: '现成模板方案',
        content: '我有一套自由职业者管理模板，包含项目、客户、财务模块，也许你不需要从零开发。',
        price: 299,
      },
    };

    return agents.map((agent, index) => ({
      ...agent,
      status: statusMap[agent.id] || 'observing',
      position: PLACEHOLDER_POSITIONS[index % PLACEHOLDER_POSITIONS.length],
      response: responseMap[agent.id],
    }));
  }, [agents]);

  // Get willing agents (green)
  const willingAgents = useMemo(
    () => agentsWithStatus.filter(a => a.status === 'willing'),
    [agentsWithStatus]
  );

  // Circle positions for converged agents
  const circlePositions = useMemo(
    () => calculateCirclePositions(willingAgents.length, 140),
    [willingAgents.length]
  );

  // Phase transition effect
  useEffect(() => {
    if (phase === 'idle') {
      // Start the animation sequence
      const timer = setTimeout(() => setPhase('launch'), 100);
      return () => clearTimeout(timer);
    }

    if (phase === 'launch') {
      const timer = setTimeout(() => setPhase('broadcast'), PHASE_TIMING.launch);
      return () => clearTimeout(timer);
    }

    if (phase === 'broadcast') {
      // Trigger multiple waves
      const waveInterval = setInterval(() => {
        setWaveCount(c => c + 1);
      }, 600);
      const timer = setTimeout(() => {
        clearInterval(waveInterval);
        setPhase('scan');
      }, PHASE_TIMING.broadcast);
      return () => {
        clearInterval(waveInterval);
        clearTimeout(timer);
      };
    }

    if (phase === 'scan') {
      // Discover agents one by one
      let index = 0;
      const interval = setInterval(() => {
        if (index < agents.length) {
          setDiscoveredAgents(prev => [...prev, index]);
          index++;
        } else {
          clearInterval(interval);
          setPhase('classify');
        }
      }, 400);
      return () => clearInterval(interval);
    }

    if (phase === 'classify') {
      const timer = setTimeout(() => setPhase('converge'), PHASE_TIMING.classify);
      return () => clearTimeout(timer);
    }

    if (phase === 'converge') {
      const timer = setTimeout(() => setPhase('respond'), PHASE_TIMING.converge);
      return () => clearTimeout(timer);
    }

    // respond phase is user-controlled, no auto-transition
  }, [phase, agents.length]);

  // Handle start negotiation
  const handleStartNegotiation = useCallback(() => {
    setPhase('negotiate');
    onStartNegotiation?.();

    // Simulate information flow
    setTimeout(() => {
      setPhase('filter');
      // Filter out xiaolin (competition didn't win)
      setFilteredAgents(['xiaolin']);
    }, PHASE_TIMING.negotiate);

    setTimeout(() => {
      setPhase('deep');
      // Simulate peer chat between laowang and notion
      setPeerChat({ agent1: 'laowang', agent2: 'notion' });
    }, PHASE_TIMING.negotiate + PHASE_TIMING.filter);

    setTimeout(() => {
      setPeerChat(null);
      setPhase('proposal');
    }, PHASE_TIMING.negotiate + PHASE_TIMING.filter + PHASE_TIMING.deep);
  }, [onStartNegotiation]);

  // Handle agent click
  const handleAgentClick = useCallback((agentId: string) => {
    setSelectedAgent(selectedAgent === agentId ? null : agentId);
  }, [selectedAgent]);

  // Get status color
  const getStatusColor = (status: AgentStatus) => {
    switch (status) {
      case 'willing': return '#10B981';
      case 'notMatch': return '#EF4444';
      case 'observing': return '#9CA3AF';
      case 'filtered': return '#EF4444';
      case 'final': return '#10B981';
      default: return '#9CA3AF';
    }
  };

  // Get response type label
  const getResponseTypeLabel = (type: ResponseType) => {
    switch (type) {
      case 'competition': return '竞标';
      case 'offer': return '报价';
      case 'suggestion': return '建议';
      default: return '';
    }
  };

  // Check if agent should be visible
  const isAgentVisible = (index: number) => {
    if (phase === 'idle' || phase === 'launch' || phase === 'broadcast') return false;
    return discoveredAgents.includes(index);
  };

  // Check if agent should show classification color
  const shouldShowClassification = () => {
    return ['classify', 'converge', 'respond', 'negotiate', 'filter', 'deep', 'proposal', 'complete'].includes(phase);
  };

  // Check if agent is in converged circle
  const isConverged = () => {
    return ['converge', 'respond', 'negotiate', 'filter', 'deep', 'proposal', 'complete'].includes(phase);
  };

  // Check if agent is filtered out
  const isFiltered = (agentId: string) => {
    return filteredAgents.includes(agentId);
  };

  // Phase labels
  const getPhaseLabel = () => {
    switch (phase) {
      case 'launch': return '发射需求...';
      case 'broadcast': return '广播扫描中...';
      case 'scan': return '发现 Agent...';
      case 'classify': return '分析匹配度...';
      case 'converge': return '汇聚响应者...';
      case 'respond': return `${willingAgents.length} 个 Agent 响应`;
      case 'negotiate': return '信息汇聚中...';
      case 'filter': return '筛选最佳方案...';
      case 'deep': return '深入协商中...';
      case 'proposal': return '方案确定';
      default: return '';
    }
  };

  return (
    <div className={styles.container} ref={containerRef}>
      {/* Phase indicator */}
      <div className={`${styles.phaseIndicator} ${phase !== 'idle' ? styles.visible : ''}`}>
        <span className={styles.phaseText}>{getPhaseLabel()}</span>
      </div>

      {/* Requirement badge - shrinks during launch */}
      <div className={`${styles.requirementBadge} ${phase === 'launch' ? styles.launching : ''} ${phase !== 'idle' && phase !== 'launch' ? styles.hidden : ''}`}>
        <span className={styles.requirementLabel}>你的需求</span>
        <p className={styles.requirementText}>{requirement}</p>
      </div>

      {/* Network visualization */}
      <div className={styles.networkContainer}>
        <svg className={styles.svg} viewBox="-250 -250 500 500">
          {/* Placeholder circles (background decoration) */}
          {PLACEHOLDER_POSITIONS.map((pos, i) => (
            <circle
              key={`placeholder-${i}`}
              cx={pos.x}
              cy={pos.y}
              r={pos.size}
              className={`${styles.placeholder} ${phase === 'broadcast' ? styles.flickering : ''}`}
              style={{ animationDelay: `${i * 0.05}s` }}
            />
          ))}

          {/* Broadcast waves */}
          {phase === 'broadcast' && Array.from({ length: waveCount }).map((_, i) => (
            <circle
              key={`wave-${i}`}
              cx="0"
              cy="0"
              r="40"
              className={styles.broadcastWave}
            />
          ))}

          {/* Launch lines */}
          {phase === 'launch' && Array.from({ length: 12 }).map((_, i) => {
            const angle = (i / 12) * Math.PI * 2;
            const endX = Math.cos(angle) * 200;
            const endY = Math.sin(angle) * 200;
            return (
              <line
                key={`launch-${i}`}
                x1="0"
                y1="0"
                x2={endX}
                y2={endY}
                className={styles.launchLine}
                style={{ animationDelay: `${i * 0.05}s` }}
              />
            );
          })}

          {/* Connection lines to center */}
          {isConverged() && willingAgents.map((agent, index) => {
            if (isFiltered(agent.id)) return null;
            const pos = circlePositions[index];
            const isPeerChatting = peerChat && (peerChat.agent1 === agent.id || peerChat.agent2 === agent.id);
            return (
              <g key={`connection-${agent.id}`}>
                <line
                  x1={pos.x}
                  y1={pos.y}
                  x2="0"
                  y2="0"
                  className={`${styles.connectionLine} ${phase === 'negotiate' ? styles.flowing : ''} ${isPeerChatting ? styles.peerActive : ''}`}
                />
                {/* Data particles flowing to center */}
                {phase === 'negotiate' && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r="4"
                    className={styles.dataParticle}
                    style={{
                      '--target-x': `${-pos.x}px`,
                      '--target-y': `${-pos.y}px`,
                    } as React.CSSProperties}
                  />
                )}
              </g>
            );
          })}

          {/* Peer-to-peer connection during deep negotiation */}
          {peerChat && (() => {
            const agent1Index = willingAgents.findIndex(a => a.id === peerChat.agent1);
            const agent2Index = willingAgents.findIndex(a => a.id === peerChat.agent2);
            if (agent1Index === -1 || agent2Index === -1) return null;
            const pos1 = circlePositions[agent1Index];
            const pos2 = circlePositions[agent2Index];
            return (
              <line
                x1={pos1.x}
                y1={pos1.y}
                x2={pos2.x}
                y2={pos2.y}
                className={styles.peerConnection}
              />
            );
          })()}
        </svg>

        {/* Center node */}
        <div className={`${styles.centerNode} ${phase === 'broadcast' ? styles.broadcasting : ''} ${phase === 'negotiate' ? styles.receiving : ''}`}>
          <div className={styles.centerNodeInner}>
            {phase === 'broadcast' ? (
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12.55a11 11 0 0 1 14.08 0" />
                <path d="M1.42 9a16 16 0 0 1 21.16 0" />
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                <circle cx="12" cy="20" r="1.5" fill="currentColor" />
              </svg>
            ) : (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
            )}
          </div>
          <span className={styles.centerLabel}>
            {phase === 'broadcast' ? '广播中' : phase === 'negotiate' ? '汇聚中' : '需求'}
          </span>
        </div>

        {/* Agent nodes - scattered during scan, converged after */}
        {agentsWithStatus.map((agent, index) => {
          if (!isAgentVisible(index)) return null;

          // Determine position based on phase
          let position = agent.position || { x: 0, y: 0 };
          const isWilling = agent.status === 'willing';
          const willingIndex = willingAgents.findIndex(a => a.id === agent.id);

          if (isConverged() && isWilling && willingIndex !== -1) {
            position = circlePositions[willingIndex];
          }

          // Hide non-willing agents after converge
          if (isConverged() && !isWilling) {
            return null;
          }

          // Hide filtered agents
          if (isFiltered(agent.id)) {
            return (
              <div
                key={agent.id}
                className={`${styles.agentNode} ${styles.filtered}`}
                style={{
                  transform: `translate(calc(${position.x}px - 50%), calc(${position.y}px - 50%))`,
                }}
              >
                <div
                  className={styles.agentAvatar}
                  style={{ borderColor: '#EF4444' }}
                >
                  <span className={styles.agentInitial}>{agent.name.charAt(0)}</span>
                </div>
              </div>
            );
          }

          const statusColor = getStatusColor(agent.status);
          const isSelected = selectedAgent === agent.id;
          const isPeerChatting = peerChat && (peerChat.agent1 === agent.id || peerChat.agent2 === agent.id);

          return (
            <div
              key={agent.id}
              className={`${styles.agentNode} ${shouldShowClassification() ? styles.classified : ''} ${isSelected ? styles.selected : ''} ${isPeerChatting ? styles.chatting : ''}`}
              style={{
                transform: `translate(calc(${position.x}px - 50%), calc(${position.y}px - 50%))`,
                '--status-color': statusColor,
              } as React.CSSProperties}
              onClick={() => handleAgentClick(agent.id)}
              onKeyDown={(e) => e.key === 'Enter' && handleAgentClick(agent.id)}
              role="button"
              tabIndex={0}
              aria-label={`Agent ${agent.name}, 点击查看详情`}
              aria-expanded={isSelected}
            >
              <div
                className={`${styles.agentAvatar} ${phase === 'respond' && isWilling ? styles.loading : ''}`}
                style={{ borderColor: shouldShowClassification() ? statusColor : 'transparent' }}
              >
                {agent.avatar ? (
                  <img src={agent.avatar} alt={agent.name} />
                ) : (
                  <span className={styles.agentInitial}>{agent.name.charAt(0)}</span>
                )}
              </div>
              <span className={styles.agentName}>{agent.name}</span>

              {/* Loading dots during respond phase */}
              {phase === 'respond' && isWilling && !agent.response && (
                <span className={styles.loadingDots}>...</span>
              )}

              {/* Response bubble with bio */}
              {isSelected && (
                <div className={styles.responseBubble}>
                  {/* Bio section - from SecondMe */}
                  {agents.find(a => a.id === agent.id)?.bio && (
                    <div className={styles.bioSection}>
                      <div className={styles.bioHeader}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        <span>来自 SecondMe</span>
                      </div>
                      <p className={styles.bioSummary}>{agents.find(a => a.id === agent.id)?.bio?.summary}</p>
                      <div className={styles.bioTags}>
                        {agents.find(a => a.id === agent.id)?.bio?.expertise.slice(0, 3).map((tag, i) => (
                          <span key={i} className={styles.bioTag}>{tag}</span>
                        ))}
                      </div>
                      <p className={styles.bioExperience}>{agents.find(a => a.id === agent.id)?.bio?.experience}</p>
                    </div>
                  )}

                  {/* Response section */}
                  {agent.response && (
                    <>
                      <div className={styles.responseDivider} />
                      <div className={styles.responseHeader}>
                        <span className={styles.responseType} style={{ backgroundColor: `${statusColor}20`, color: statusColor }}>
                          {getResponseTypeLabel(agent.response.type)}
                        </span>
                        <span className={styles.responseTitle}>{agent.response.title}</span>
                      </div>
                      <p className={styles.responseContent}>{agent.response.content}</p>
                      {agent.response.conditions && (
                        <div className={styles.responseConditions}>
                          {agent.response.conditions.map((c, i) => (
                            <span key={i} className={styles.condition}>{c}</span>
                          ))}
                        </div>
                      )}
                      {agent.response.price && (
                        <div className={styles.responsePrice}>
                          <span className={styles.priceLabel}>报价</span>
                          <span className={styles.priceValue}>{agent.response.price} 元</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Peer chat bubble */}
              {isPeerChatting && (
                <div className={styles.peerChatBubble}>
                  {agent.id === 'laowang' ? '我觉得可以结合模板方案...' : '对，这样成本更低'}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Action area */}
      <div className={`${styles.actionArea} ${phase === 'respond' ? styles.visible : ''}`}>
        <p className={styles.responseCount}>
          <span className={styles.countNumber}>{willingAgents.length}</span>
          个 Agent 响应了你的需求
        </p>
        <p className={styles.hint}>点击 Agent 查看详细回应</p>
        <button
          className={styles.startButton}
          onClick={handleStartNegotiation}
        >
          开始协商
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>

      {/* Proposal action area */}
      <div className={`${styles.actionArea} ${phase === 'proposal' ? styles.visible : ''}`}>
        <p className={styles.proposalTitle}>方案已确定</p>
        <p className={styles.proposalDesc}>
          {willingAgents.filter(a => !isFiltered(a.id)).length} 个 Agent 将参与你的项目
        </p>
        <button
          className={styles.startButton}
          onClick={onComplete}
        >
          查看详细方案
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  );
}
