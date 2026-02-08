'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import {
  DemoStage,
  Agent,
  EventCard,
  EventCardType,
  Proposal,
  ProposalStep,
  KeyInsight,
  TimelineEvent,
} from './shared/types';
import { StageIndicator } from './StageIndicator/StageIndicator';
import { RequirementInput } from './Stage1-Input/RequirementInput';
import { NetworkGraph } from './Stage2-Response/NetworkGraph';
import { NetworkGraphV2 } from './NetworkGraphV2/NetworkGraphV2';
import { NegotiationLayout } from './Stage3-Negotiation/NegotiationLayout';
import { ProposalComparison } from './Stage4-Proposal/ProposalComparison';
import { SummaryLayout } from './Stage5-Summary/SummaryLayout';
import { useNegotiation, NegotiationStatus } from '@/hooks/useNegotiation';
import { NegotiationMessage } from '@/types/experience';
import styles from './ExperienceV2.module.css';

// ============ Message Conversion Utilities ============

/**
 * Convert backend WebSocket message to frontend EventCard format
 * Backend message types: text, system, offer, question, challenge, insight, response, update
 * Frontend EventCard types: insight, transform, combine, confirm
 *
 * @param tMock - translation function for DemandNegotiation.mock namespace
 */
function convertMessageToEventCard(
  message: NegotiationMessage,
  index: number,
  tMock: (key: string, values?: Record<string, string>) => string
): EventCard | null {
  // Skip system messages that are just status updates
  if (message.message_type === 'system') {
    const content = message.content.toLowerCase();
    // Skip coordinator status messages
    if (
      content.includes('正在分析') ||
      content.includes('已识别') ||
      content.includes('正在邀请') ||
      content.includes('正在生成')
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
    title = tMock('cognitiveShift');
  } else if (
    content.includes('组合') ||
    content.includes('方案') ||
    content.includes('建议这样')
  ) {
    eventType = 'combine';
    title = tMock('proposalCombine');
  } else if (
    content.includes('确认') ||
    content.includes('达成共识') ||
    content.includes('协商完成')
  ) {
    eventType = 'confirm';
    title = tMock('proposalConfirm');
  } else if (
    content.includes('意外发现') ||
    content.includes('💡') ||
    content.includes('发现')
  ) {
    eventType = 'insight';
    title = tMock('unexpectedDiscovery');
  } else if (content.includes('问') || content.includes('？')) {
    eventType = 'insight';
    title = tMock('demandClarify');
  } else {
    eventType = 'insight';
    title = tMock('agentViewpoint', { name: senderName });
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
function convertMessagesToEvents(
  messages: NegotiationMessage[],
  tMock: (key: string, values?: Record<string, string>) => string
): EventCard[] {
  const events: EventCard[] = [];

  messages.forEach((msg, index) => {
    const event = convertMessageToEventCard(msg, index, tMock);
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

// ============ Mock Data Builders (Fallback) ============

type TFunc = (key: string) => string;

function buildMockAgents(t: TFunc): Agent[] {
  return [
    {
      id: 'alex',
      name: t('alexName'),
      role: t('alexRole'),
      description: t('alexDesc'),
      skills: t('alexSkills').split(','),
      initialResponse: t('alexResponse'),
      bio: {
        summary: t('alexBioSummary'),
        expertise: t('alexBioExpertise').split(','),
        experience: t('alexBioExp'),
        style: t('alexBioStyle'),
      },
    },
    {
      id: 'xiaolin',
      name: t('xiaolinName'),
      role: t('xiaolinRole'),
      description: t('xiaolinDesc'),
      skills: t('xiaolinSkills').split(','),
      initialResponse: t('xiaolinResponse'),
      bio: {
        summary: t('xiaolinBioSummary'),
        expertise: t('xiaolinBioExpertise').split(','),
        experience: t('xiaolinBioExp'),
        style: t('xiaolinBioStyle'),
      },
    },
    {
      id: 'studio',
      name: t('studioName'),
      role: t('studioRole'),
      description: t('studioDesc'),
      skills: t('studioSkills').split(','),
      initialResponse: t('studioResponse'),
      bio: {
        summary: t('studioBioSummary'),
        expertise: t('studioBioExpertise').split(','),
        experience: t('studioBioExp'),
        style: t('studioBioStyle'),
      },
    },
    {
      id: 'cursor',
      name: t('cursorName'),
      role: t('cursorRole'),
      description: t('cursorDesc'),
      skills: t('cursorSkills').split(','),
      initialResponse: t('cursorResponse'),
      bio: {
        summary: t('cursorBioSummary'),
        expertise: t('cursorBioExpertise').split(','),
        experience: t('cursorBioExp'),
        style: t('cursorBioStyle'),
      },
    },
    {
      id: 'laowang',
      name: t('laowangName'),
      role: t('laowangRole'),
      description: t('laowangDesc'),
      skills: t('laowangSkills').split(','),
      initialResponse: t('laowangResponse'),
      bio: {
        summary: t('laowangBioSummary'),
        expertise: t('laowangBioExpertise').split(','),
        experience: t('laowangBioExp'),
        style: t('laowangBioStyle'),
      },
    },
    {
      id: 'notion',
      name: t('notionName'),
      role: t('notionRole'),
      description: t('notionDesc'),
      skills: t('notionSkills').split(','),
      initialResponse: t('notionResponse'),
      bio: {
        summary: t('notionBioSummary'),
        expertise: t('notionBioExpertise').split(','),
        experience: t('notionBioExp'),
        style: t('notionBioStyle'),
      },
    },
    {
      id: 'bubble',
      name: t('bubbleName'),
      role: t('bubbleRole'),
      description: t('bubbleDesc'),
      skills: t('bubbleSkills').split(','),
      initialResponse: t('bubbleResponse'),
      bio: {
        summary: t('bubbleBioSummary'),
        expertise: t('bubbleBioExpertise').split(','),
        experience: t('bubbleBioExp'),
        style: t('bubbleBioStyle'),
      },
    },
  ];
}

function buildMockEvents(t: TFunc): EventCard[] {
  return [
    {
      id: '1',
      type: 'insight',
      title: t('event1Title'),
      content: t('event1Content'),
      timestamp: Date.now() - 300000,
      agents: ['laowang'],
    },
    {
      id: '2',
      type: 'transform',
      title: t('event2Title'),
      content: t('event2Content'),
      timestamp: Date.now() - 240000,
      agents: ['laowang', 'notion'],
    },
    {
      id: '3',
      type: 'combine',
      title: t('event3Title'),
      content: t('event3Content'),
      timestamp: Date.now() - 180000,
      agents: ['notion', 'cursor', 'alex'],
    },
    {
      id: '4',
      type: 'confirm',
      title: t('event4Title'),
      content: t('event4Content'),
      timestamp: Date.now() - 120000,
      agents: ['notion', 'cursor', 'alex'],
    },
  ];
}

function buildMockProposal(t: TFunc, mockAgents: Agent[]): Proposal {
  return {
    steps: [
      {
        id: '1',
        order: 1,
        agentId: 'laowang',
        agentName: t('laowangName'),
        description: t('step1Desc'),
        price: 500,
        duration: t('step1Duration'),
      },
      {
        id: '2',
        order: 2,
        agentId: 'notion',
        agentName: t('notionName'),
        description: t('step2Desc'),
        price: 299,
        duration: t('step2Duration'),
      },
      {
        id: '3',
        order: 3,
        agentId: 'cursor',
        agentName: t('cursorName'),
        description: t('step3Desc'),
        price: 200,
        duration: t('step3Duration'),
      },
      {
        id: '4',
        order: 4,
        agentId: 'alex',
        agentName: t('alexName'),
        description: t('step4Desc'),
        price: 2000,
        duration: t('step4Duration'),
      },
    ],
    totalCost: 2999,
    originalCost: 50000,
    participants: mockAgents.filter((a) =>
      ['laowang', 'notion', 'cursor', 'alex'].includes(a.id)
    ),
  };
}

function buildMockInsights(t: TFunc): KeyInsight[] {
  return [
    {
      type: 'insight',
      title: t('insight1Title'),
      content: t('insight1Content'),
    },
    {
      type: 'transform',
      title: t('insight2Title'),
      content: t('insight2Content'),
    },
    {
      type: 'discovery',
      title: t('insight3Title'),
      content: t('insight3Content'),
    },
  ];
}

export function ExperienceV2Page() {
  const tMock = useTranslations('DemandNegotiation.mock');
  const tSummary = useTranslations('DemandNegotiation.summary');
  const tExp = useTranslations('DemandNegotiation.experience');

  // ============ Memoized Mock Data ============
  const MOCK_AGENTS = useMemo(() => buildMockAgents(tExp), [tExp]);
  const MOCK_EVENTS = useMemo(() => buildMockEvents(tExp), [tExp]);
  const MOCK_PROPOSAL = useMemo(() => buildMockProposal(tExp, MOCK_AGENTS), [tExp, MOCK_AGENTS]);
  const MOCK_INSIGHTS = useMemo(() => buildMockInsights(tExp), [tExp]);

  // ============ State ============
  const [currentStage, setCurrentStage] = useState<DemoStage>('input');
  const [completedStages, setCompletedStages] = useState<DemoStage[]>([]);
  const [requirement, setRequirement] = useState('');
  const [isPlaying, setIsPlaying] = useState(true);
  const [localEvents, setLocalEvents] = useState<EventCard[]>([]);
  const [activeConnections, setActiveConnections] = useState<
    { from: string; to: string }[]
  >([]);
  const [useV2Graph] = useState(true);
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

  // Ref for interval cleanup (fallback mode)
  const negotiationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastProcessedMessageCount = useRef(0);

  // ============ Derived State ============
  // Convert backend messages to EventCards
  const realEvents = useMemo(() => {
    return convertMessagesToEvents(messages, tMock);
  }, [messages, tMock]);

  // Use real events if available, otherwise use local events (fallback)
  const events = realEvents.length > 0 ? realEvents : localEvents;

  // Extract agents from messages or use mock agents
  const displayAgents = useMemo(() => {
    const extractedAgents = extractAgentsFromMessages(messages);
    return extractedAgents.length > 0 ? extractedAgents : MOCK_AGENTS;
  }, [messages, MOCK_AGENTS]);

  // Build proposal from result or use mock
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
            price: typeof task.price === 'number' ? task.price : 0,
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
        return MOCK_PROPOSAL;
      }
    }
    return MOCK_PROPOSAL;
  }, [result, finalProposal, displayAgents, MOCK_PROPOSAL]);

  // Build insights from events
  const insights = useMemo(() => {
    if (events.length === 0) {
      return MOCK_INSIGHTS;
    }

    const generatedInsights: KeyInsight[] = [];

    // Find insight events
    const insightEvents = events.filter((e) => e.type === 'insight');
    if (insightEvents.length > 0) {
      generatedInsights.push({
        type: 'insight',
        title: tMock('demandReconstruct'),
        content: insightEvents[0].content.slice(0, 100),
      });
    }

    // Find transform events
    const transformEvents = events.filter((e) => e.type === 'transform');
    if (transformEvents.length > 0) {
      generatedInsights.push({
        type: 'transform',
        title: tMock('cognitiveShift'),
        content: transformEvents[0].content.slice(0, 100),
      });
    }

    // Find combine events as discovery
    const combineEvents = events.filter((e) => e.type === 'combine');
    if (combineEvents.length > 0) {
      generatedInsights.push({
        type: 'discovery',
        title: tMock('unexpectedDiscovery'),
        content: combineEvents[0].content.slice(0, 100),
      });
    }

    return generatedInsights.length > 0 ? generatedInsights : MOCK_INSIGHTS;
  }, [events, tMock, MOCK_INSIGHTS]);

  // ============ Effects ============

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (negotiationIntervalRef.current) {
        clearInterval(negotiationIntervalRef.current);
      }
    };
  }, []);

  // Monitor negotiation status changes
  useEffect(() => {
    if (negotiationStatus === 'completed' && currentStage === 'response') {
      // Negotiation completed, move to proposal stage
      completeStage('response');
      setCurrentStage('proposal');
    }
  }, [negotiationStatus, currentStage]);

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

  // ============ Callbacks ============

  const goToStage = useCallback((stage: DemoStage) => {
    setCurrentStage(stage);
  }, []);

  const completeStage = useCallback((stage: DemoStage) => {
    setCompletedStages((prev) => {
      if (prev.includes(stage)) return prev;
      return [...prev, stage];
    });
  }, []);

  // Stage 1: Submit requirement
  const handleSubmitRequirement = useCallback(
    async (text: string) => {
      setRequirement(text);
      completeStage('input');
      setCurrentStage('response');

      // Submit to backend API
      try {
        await submitRequirement({
          title: text.slice(0, 50),
          description: text,
        });
        console.log('[ExperienceV2] Requirement submitted to backend');
      } catch (error) {
        console.error('[ExperienceV2] Failed to submit requirement:', error);
        // Continue with mock data as fallback
      }
    },
    [completeStage, submitRequirement]
  );

  // Stage 2: Start negotiation (for non-V2 graph)
  const handleStartNegotiation = useCallback(() => {
    completeStage('response');
    setCurrentStage('negotiation');

    // If we have real messages, don't use mock simulation
    if (messages.length > 0) {
      return;
    }

    // Fallback: Simulate events appearing with mock data
    if (negotiationIntervalRef.current) {
      clearInterval(negotiationIntervalRef.current);
    }

    let eventIndex = 0;
    negotiationIntervalRef.current = setInterval(() => {
      if (eventIndex < MOCK_EVENTS.length) {
        setLocalEvents((prev) => [...prev, MOCK_EVENTS[eventIndex]]);

        const event = MOCK_EVENTS[eventIndex];
        if (event.agents && event.agents.length > 1) {
          setActiveConnections(
            event.agents.slice(0, -1).map((from, i) => ({
              from,
              to: event.agents![i + 1],
            }))
          );
        }

        eventIndex++;
      } else {
        if (negotiationIntervalRef.current) {
          clearInterval(negotiationIntervalRef.current);
          negotiationIntervalRef.current = null;
        }
        setActiveConnections([]);
      }
    }, 2000);
  }, [completeStage, messages.length, MOCK_EVENTS]);

  // Stage 3: Controls
  const handleTogglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const handleSpeedUp = useCallback(() => {
    // Speed up animation - could be implemented later
  }, []);

  const handleSkipToResult = useCallback(() => {
    // Use real events if available, otherwise mock
    if (realEvents.length === 0) {
      setLocalEvents(MOCK_EVENTS);
    }
    completeStage('negotiation');
    setCurrentStage('proposal');
  }, [completeStage, realEvents.length, MOCK_EVENTS]);

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
    setLocalEvents([]);
    setActiveConnections([]);
    setFinalProposal(null);
    lastProcessedMessageCount.current = 0;
    resetNegotiation();
  }, [resetNegotiation]);

  const handleShare = useCallback(() => {
    alert(tSummary('shareComing'));
  }, [tSummary]);

  const handleLearnMore = useCallback(() => {
    window.open('/', '_blank');
  }, []);

  // ============ Render ============
  const renderStage = () => {
    switch (currentStage) {
      case 'input':
        return <RequirementInput onSubmit={handleSubmitRequirement} />;

      case 'response':
        return useV2Graph ? (
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
        ) : (
          <NetworkGraph
            requirement={requirement}
            agents={displayAgents}
            onStartNegotiation={handleStartNegotiation}
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
            originalRisk={tExp('riskHigh')}
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
      {/* Debug info - can be removed in production */}
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
          WS: {wsStatus} | Messages: {messages.length} | Status:{' '}
          {negotiationStatus}
        </div>
      )}
    </div>
  );
}
