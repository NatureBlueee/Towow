'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  DemoStage,
  Agent,
  EventCard,
  EventCardType,
  Proposal,
  ProposalStep,
  KeyInsight,
  TimelineEvent,
} from '../experience-v2/shared/types';
import { StageIndicator } from '../experience-v2/StageIndicator/StageIndicator';
import { RequirementInput } from '../experience-v2/Stage1-Input/RequirementInput';
import { NetworkGraphV2 } from '../experience-v2/NetworkGraphV2/NetworkGraphV2';
import { NegotiationLayout } from '../experience-v2/Stage3-Negotiation/NegotiationLayout';
import { ProposalComparison } from '../experience-v2/Stage4-Proposal/ProposalComparison';
import { SummaryLayout } from '../experience-v2/Stage5-Summary/SummaryLayout';
import { useNegotiation, NegotiationStatus } from '@/hooks/useNegotiation';
import { NegotiationMessage } from '@/types/experience';
import styles from '../experience-v2/ExperienceV2.module.css';

// ============ Message Conversion Utilities ============

/**
 * Convert backend WebSocket message to frontend EventCard format
 *
 * Backend message types from simulate_negotiation:
 * - type: "message" with payload containing message_type: text | system | action
 * - type: "phase_start" with payload containing phase_name, description
 * - type: "negotiation_complete" with payload containing final_proposal
 *
 * Frontend EventCard types: insight, transform, combine, confirm
 */
function convertMessageToEventCard(
  message: NegotiationMessage,
  index: number
): EventCard | null {
  // Skip system messages that are just status updates
  if (message.message_type === 'system') {
    const content = message.content.toLowerCase();
    // Skip coordinator status messages (Chinese and English)
    if (
      content.includes('正在分析') ||
      content.includes('analyzing') ||
      content.includes('已识别') ||
      content.includes('identified') ||
      content.includes('正在邀请') ||
      content.includes('inviting') ||
      content.includes('正在生成') ||
      content.includes('generating')
    ) {
      return null;
    }
  }

  // Determine EventCard type based on message content and metadata
  let eventType: EventCardType = 'insight';
  let title = '';

  const content = message.content;
  const senderName = message.sender_name || message.sender_id;

  // Analyze message content to determine type
  if (
    content.includes('认知转变') ||
    content.includes('转变') ||
    content.includes('发现真正需要')
  ) {
    eventType = 'transform';
    title = '认知转变';
  } else if (
    content.includes('组合') ||
    content.includes('方案') ||
    content.includes('建议这样')
  ) {
    eventType = 'combine';
    title = '方案组合';
  } else if (
    content.includes('确认') ||
    content.includes('达成共识') ||
    content.includes('协商完成')
  ) {
    eventType = 'confirm';
    title = '方案确认';
  } else if (
    content.includes('意外发现') ||
    content.includes('发现')
  ) {
    eventType = 'insight';
    title = '意外发现';
  } else if (content.includes('问') || content.includes('？')) {
    eventType = 'insight';
    title = '需求澄清';
  } else {
    eventType = 'insight';
    title = `${senderName}的观点`;
  }

  return {
    id: message.message_id || `event-${index}`,
    type: eventType,
    title,
    content: `${senderName}: ${content}`,
    timestamp: new Date(message.timestamp).getTime(),
    agents: [message.sender_id],
  };
}

/**
 * Convert backend messages to EventCard array
 */
function convertMessagesToEvents(messages: NegotiationMessage[]): EventCard[] {
  const events: EventCard[] = [];

  messages.forEach((msg, index) => {
    const event = convertMessageToEventCard(msg, index);
    if (event) {
      events.push(event);
    }
  });

  return events;
}

/**
 * Extract agents from messages
 */
function extractAgentsFromMessages(messages: NegotiationMessage[]): Agent[] {
  const agentMap = new Map<string, Agent>();

  messages.forEach((msg) => {
    if (
      msg.sender_id &&
      msg.sender_id !== 'system' &&
      msg.sender_id !== 'coordinator' &&
      msg.sender_id !== 'channel_admin' &&
      msg.sender_id !== 'user_agent' &&
      !agentMap.has(msg.sender_id)
    ) {
      agentMap.set(msg.sender_id, {
        id: msg.sender_id,
        name: msg.sender_name || msg.sender_id,
        role: 'Agent',
        description: '',
        skills: [],
        initialResponse: msg.content.slice(0, 50) + '...',
      });
    }
  });

  return Array.from(agentMap.values());
}

// ============ Default Agents (used when no real agents available) ============

const DEFAULT_AGENTS: Agent[] = [
  {
    id: 'agent_1',
    name: 'Agent 1',
    role: 'AI Assistant',
    description: 'Waiting for real agents...',
    skills: [],
    initialResponse: '',
  },
];

export function ExperienceV3Page() {
  // ============ State ============
  const [currentStage, setCurrentStage] = useState<DemoStage>('input');
  const [completedStages, setCompletedStages] = useState<DemoStage[]>([]);
  const [requirement, setRequirement] = useState('');
  const [isPlaying, setIsPlaying] = useState(true);
  const [activeConnections, setActiveConnections] = useState<
    { from: string; to: string }[]
  >([]);
  const [finalProposal, setFinalProposal] = useState<Proposal | null>(null);

  // ============ Hooks ============
  // Use the negotiation hook for real backend communication
  const {
    submitRequirement,
    messages,
    negotiationStatus,
    result,
    reset: resetNegotiation,
    wsStatus,
  } = useNegotiation();

  const lastProcessedMessageCount = useRef(0);

  // ============ Derived State ============
  // Convert backend messages to EventCards
  const events = useMemo(() => {
    return convertMessagesToEvents(messages);
  }, [messages]);

  // Extract agents from messages
  const displayAgents = useMemo(() => {
    const extractedAgents = extractAgentsFromMessages(messages);
    return extractedAgents.length > 0 ? extractedAgents : DEFAULT_AGENTS;
  }, [messages]);

  // Build proposal from result
  const proposal = useMemo(() => {
    if (finalProposal) {
      return finalProposal;
    }
    if (result?.final_proposal) {
      // Try to parse final_proposal if it's a string
      try {
        const proposalData =
          typeof result.final_proposal === 'string'
            ? JSON.parse(result.final_proposal)
            : result.final_proposal;

        // Convert backend proposal format to frontend format
        const steps: ProposalStep[] = (proposalData.tasks || []).map(
          (task: { agent?: string; task?: string; price?: number | string; timeline?: string }, index: number) => ({
            id: String(index + 1),
            order: index + 1,
            agentId: task.agent?.toLowerCase().replace(/\s+/g, '_') || `agent_${index}`,
            agentName: task.agent || 'Unknown',
            description: task.task || '',
            price: typeof task.price === 'number'
              ? task.price
              : typeof task.price === 'string'
                ? parseInt(task.price.replace(/[^\d]/g, ''), 10) || 0
                : 0,
            duration: task.timeline || '',
          })
        );

        const totalCost =
          proposalData.budget?.total_estimated ||
          steps.reduce((sum: number, s: ProposalStep) => sum + (s.price || 0), 0);

        return {
          steps,
          totalCost: typeof totalCost === 'number' ? totalCost : 1000,
          originalCost: 50000,
          participants: displayAgents.slice(0, steps.length),
        };
      } catch {
        // Return empty proposal if parsing fails
        return {
          steps: [],
          totalCost: 0,
          originalCost: 50000,
          participants: [],
        };
      }
    }
    // Return empty proposal when no result yet
    return {
      steps: [],
      totalCost: 0,
      originalCost: 50000,
      participants: [],
    };
  }, [result, finalProposal, displayAgents]);

  // Build insights from events
  const insights = useMemo(() => {
    if (events.length === 0) {
      return [];
    }

    const generatedInsights: KeyInsight[] = [];

    // Find insight events
    const insightEvents = events.filter((e) => e.type === 'insight');
    if (insightEvents.length > 0) {
      generatedInsights.push({
        type: 'insight',
        title: '需求重构',
        content: insightEvents[0].content.slice(0, 100),
      });
    }

    // Find transform events
    const transformEvents = events.filter((e) => e.type === 'transform');
    if (transformEvents.length > 0) {
      generatedInsights.push({
        type: 'transform',
        title: '认知转变',
        content: transformEvents[0].content.slice(0, 100),
      });
    }

    // Find combine events as discovery
    const combineEvents = events.filter((e) => e.type === 'combine');
    if (combineEvents.length > 0) {
      generatedInsights.push({
        type: 'discovery',
        title: '意外发现',
        content: combineEvents[0].content.slice(0, 100),
      });
    }

    return generatedInsights;
  }, [events]);

  // ============ Callbacks (defined before effects that use them) ============

  const goToStage = useCallback((stage: DemoStage) => {
    setCurrentStage(stage);
  }, []);

  const completeStage = useCallback((stage: DemoStage) => {
    setCompletedStages((prev) => {
      if (prev.includes(stage)) return prev;
      return [...prev, stage];
    });
  }, []);

  // ============ Effects ============

  // Monitor negotiation status changes
  useEffect(() => {
    if (negotiationStatus === 'completed' && currentStage === 'response') {
      // Negotiation completed, move to proposal stage
      completeStage('response');
      setCurrentStage('proposal');
    }
  }, [negotiationStatus, currentStage, completeStage]);

  // Update active connections based on new messages
  useEffect(() => {
    if (messages.length > lastProcessedMessageCount.current) {
      const newMessages = messages.slice(lastProcessedMessageCount.current);
      lastProcessedMessageCount.current = messages.length;

      // Create connections between consecutive message senders
      if (newMessages.length > 0) {
        const lastMsg = newMessages[newMessages.length - 1];
        if (
          lastMsg.sender_id !== 'system' &&
          lastMsg.sender_id !== 'coordinator'
        ) {
          // Find previous non-system sender
          const prevSenders = messages
            .slice(0, -1)
            .filter(
              (m) => m.sender_id !== 'system' && m.sender_id !== 'coordinator'
            )
            .map((m) => m.sender_id);

          if (prevSenders.length > 0) {
            const prevSender = prevSenders[prevSenders.length - 1];
            setActiveConnections([{ from: prevSender, to: lastMsg.sender_id }]);

            // Clear connection after a delay
            setTimeout(() => {
              setActiveConnections([]);
            }, 2000);
          }
        }
      }
    }
  }, [messages]);

  // ============ Timeline ============
  const timeline: TimelineEvent[] = useMemo(() => {
    const now = Date.now();
    return completedStages.map((stage, index) => ({
      id: `${stage}-${index}`,
      stage,
      timestamp: now - (completedStages.length - index) * 60000,
      label: stage,
    }));
  }, [completedStages]);

  // ============ More Callbacks ============

  // Stage 1: Submit requirement
  const handleSubmitRequirement = useCallback(
    async (text: string) => {
      setRequirement(text);

      // Submit to backend API
      try {
        await submitRequirement({
          title: text.slice(0, 50),
          description: text,
        });
        console.log('[ExperienceV3] Requirement submitted to backend');
        // Only transition stages after successful submission
        completeStage('input');
        setCurrentStage('response');
      } catch (error) {
        console.error('[ExperienceV3] Failed to submit requirement:', error);
        // Show error feedback to user
        alert('提交失败，请稍后重试');
      }
    },
    [completeStage, submitRequirement]
  );

  // Stage 3: Controls
  const handleTogglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const handleSpeedUp = useCallback(() => {
    // Speed up animation - could be implemented later
  }, []);

  const handleSkipToResult = useCallback(() => {
    completeStage('negotiation');
    setCurrentStage('proposal');
  }, [completeStage]);

  // Stage 4: Continue to summary
  const handleContinueToSummary = useCallback(() => {
    completeStage('proposal');
    setCurrentStage('summary');
  }, [completeStage]);

  // Stage 5: Actions
  const handleRestart = useCallback(() => {
    setCurrentStage('input');
    setCompletedStages([]);
    setRequirement('');
    setActiveConnections([]);
    setFinalProposal(null);
    lastProcessedMessageCount.current = 0;
    resetNegotiation();
  }, [resetNegotiation]);

  const handleShare = useCallback(() => {
    alert('分享功能即将上线');
  }, []);

  const handleLearnMore = useCallback(() => {
    window.open('/', '_blank');
  }, []);

  // ============ Render ============
  const renderStage = () => {
    switch (currentStage) {
      case 'input':
        return <RequirementInput onSubmit={handleSubmitRequirement} />;

      case 'response':
        return (
          <NetworkGraphV2
            requirement={requirement}
            agents={displayAgents}
            onComplete={() => {
              completeStage('response');
              setCurrentStage('proposal');
            }}
            onStartNegotiation={() => {
              // The V2 graph handles negotiation internally
            }}
          />
        );

      case 'negotiation':
        return (
          <NegotiationLayout
            agents={displayAgents}
            events={events}
            isPlaying={isPlaying}
            onTogglePlay={handleTogglePlay}
            onSpeedUp={handleSpeedUp}
            onSkipToResult={handleSkipToResult}
            activeConnections={activeConnections}
          />
        );

      case 'proposal':
        return (
          <ProposalComparison
            requirement={requirement}
            originalCost={50000}
            originalRisk="高"
            proposal={proposal}
            onContinue={handleContinueToSummary}
          />
        );

      case 'summary':
        return (
          <SummaryLayout
            timeline={timeline}
            insights={insights}
            onRestart={handleRestart}
            onShare={handleShare}
            onLearnMore={handleLearnMore}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className={styles.page}>
      <StageIndicator
        currentStage={currentStage}
        completedStages={completedStages}
        onStageClick={goToStage}
      />
      <main className={styles.main}>{renderStage()}</main>
      {/* Debug info - shows real backend connection status */}
      {process.env.NODE_ENV === 'development' && (
        <div
          style={{
            position: 'fixed',
            bottom: 10,
            right: 10,
            background: 'rgba(0,0,0,0.7)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: 4,
            fontSize: 12,
            zIndex: 9999,
          }}
        >
          <div>V3 Business Mode</div>
          <div>WS: {wsStatus} | Messages: {messages.length}</div>
          <div>Status: {negotiationStatus}</div>
        </div>
      )}
    </div>
  );
}
