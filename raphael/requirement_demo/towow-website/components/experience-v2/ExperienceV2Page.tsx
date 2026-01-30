'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  DemoStage,
  Agent,
  EventCard,
  Proposal,
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
import styles from './ExperienceV2.module.css';

// Mock data for demo
const MOCK_AGENTS: Agent[] = [
  {
    id: 'alex',
    name: '程序员Alex',
    role: '全栈开发',
    description: '5年全栈开发经验，擅长快速原型开发',
    skills: ['React', 'Node.js', 'PostgreSQL'],
    initialResponse: '我可以帮你快速搭建MVP',
    bio: {
      summary: '热爱技术的全栈工程师，专注于帮助创业者快速实现产品想法。',
      expertise: ['快速原型开发', 'MVP构建', '技术架构设计'],
      experience: '曾帮助20+创业团队从0到1搭建产品',
      style: '高效务实，注重结果导向',
    },
  },
  {
    id: 'xiaolin',
    name: '程序员小林',
    role: '后端开发',
    description: '专注后端架构和数据库设计',
    skills: ['Python', 'Django', 'AWS'],
    initialResponse: '后端架构我很熟悉',
    bio: {
      summary: '后端架构专家，擅长设计高可用、可扩展的系统。',
      expertise: ['分布式系统', '数据库优化', 'API设计'],
      experience: '8年后端开发经验，服务过千万级用户产品',
      style: '严谨细致，追求代码质量',
    },
  },
  {
    id: 'studio',
    name: '外包工作室',
    role: '开发团队',
    description: '提供完整的软件开发服务',
    skills: ['项目管理', '全栈开发', 'UI设计'],
    initialResponse: '我们可以承接整个项目',
    bio: {
      summary: '专业软件外包团队，提供从设计到开发的一站式服务。',
      expertise: ['项目管理', '团队协作', '交付保障'],
      experience: '累计交付100+项目，客户满意度98%',
      style: '流程规范，按时交付',
    },
  },
  {
    id: 'cursor',
    name: 'Cursor',
    role: 'AI编程助手',
    description: 'AI驱动的编程工具，提升开发效率',
    skills: ['代码生成', '代码补全', '重构'],
    initialResponse: '用AI加速开发',
    bio: {
      summary: 'AI驱动的智能编程助手，让编程更高效。',
      expertise: ['代码生成', '智能补全', '代码重构'],
      experience: '已帮助10万+开发者提升3倍开发效率',
      style: '智能高效，持续学习',
    },
  },
  {
    id: 'laowang',
    name: '产品教练老王',
    role: '产品顾问',
    description: '10年产品经验，帮助创业者理清需求',
    skills: ['产品规划', '用户研究', '商业模式'],
    initialResponse: '先聊聊你真正想解决什么问题',
    bio: {
      summary: '资深产品教练，专注帮助创业者找到真正的产品方向。',
      expertise: ['需求分析', '产品定位', '商业模式设计'],
      experience: '辅导过50+创业项目，多个项目获得融资',
      style: '善于提问，启发思考',
    },
  },
  {
    id: 'notion',
    name: 'Notion模板作者',
    role: '效率工具',
    description: '提供现成的管理模板和工作流',
    skills: ['Notion', '工作流设计', '模板'],
    initialResponse: '也许你不需要开发，用模板就够了',
    bio: {
      summary: 'Notion资深玩家，专注打造高效工作流模板。',
      expertise: ['工作流设计', '知识管理', '团队协作'],
      experience: '模板被5000+用户使用，好评率99%',
      style: '简洁实用，开箱即用',
    },
  },
  {
    id: 'bubble',
    name: 'Bubble',
    role: '无代码平台',
    description: '无代码快速构建Web应用',
    skills: ['无代码开发', '快速原型', '自动化'],
    initialResponse: '无代码也能做出专业应用',
    bio: {
      summary: '无代码开发专家，让非技术人员也能构建专业应用。',
      expertise: ['无代码开发', '流程自动化', '快速迭代'],
      experience: '帮助1000+非技术创业者实现产品想法',
      style: '降低门槛，快速验证',
    },
  },
];

const MOCK_EVENTS: EventCard[] = [
  {
    id: '1',
    type: 'insight',
    title: '需求本质分析',
    content:
      '产品教练老王指出：你说想找技术合伙人，但真正的需求是"快速验证想法是否可行"。技术合伙人是手段，不是目的。',
    timestamp: Date.now() - 300000,
    agents: ['laowang'],
  },
  {
    id: '2',
    type: 'transform',
    title: '认知转变',
    content:
      '从"找人一起做产品"转变为"用最小成本验证需求"。这个转变让更多解决方案成为可能。',
    timestamp: Date.now() - 240000,
    agents: ['laowang', 'notion'],
  },
  {
    id: '3',
    type: 'combine',
    title: '方案组合',
    content:
      'Notion模板 + Cursor AI编程 + 程序员Alex的指导，形成了一个低成本快速验证的组合方案。',
    timestamp: Date.now() - 180000,
    agents: ['notion', 'cursor', 'alex'],
  },
  {
    id: '4',
    type: 'confirm',
    title: '方案确认',
    content:
      '各方确认分工：Notion提供管理模板，Cursor辅助开发，Alex提供技术指导，总成本从预期的5万降到8千。',
    timestamp: Date.now() - 120000,
    agents: ['notion', 'cursor', 'alex'],
  },
];

const MOCK_PROPOSAL: Proposal = {
  steps: [
    {
      id: '1',
      order: 1,
      agentId: 'laowang',
      agentName: '产品教练老王',
      description: '1小时需求梳理，明确核心功能和验证指标',
      price: 500,
      duration: '1小时',
    },
    {
      id: '2',
      order: 2,
      agentId: 'notion',
      agentName: 'Notion模板作者',
      description: '提供自由职业者管理模板，包含项目、客户、财务模块',
      price: 299,
      duration: '即时',
    },
    {
      id: '3',
      order: 3,
      agentId: 'cursor',
      agentName: 'Cursor',
      description: '使用AI辅助开发自定义功能，提升3倍效率',
      price: 200,
      duration: '1个月',
    },
    {
      id: '4',
      order: 4,
      agentId: 'alex',
      agentName: '程序员Alex',
      description: '每周2小时技术指导，解决开发中的难题',
      price: 2000,
      duration: '1个月',
    },
  ],
  totalCost: 2999,
  originalCost: 50000,
  participants: MOCK_AGENTS.filter((a) =>
    ['laowang', 'notion', 'cursor', 'alex'].includes(a.id)
  ),
};

const MOCK_INSIGHTS: KeyInsight[] = [
  {
    type: 'insight',
    title: '需求重构',
    content: '你以为需要"技术合伙人"，实际需要的是"快速验证需求的能力"',
  },
  {
    type: 'transform',
    title: '认知转变',
    content: '从"找人做产品"到"用工具验证想法"，降低了90%的启动成本',
  },
  {
    type: 'discovery',
    title: '意外发现',
    content: 'Notion模板已经能满足80%的管理需求，无需从零开发',
  },
];

export function ExperienceV2Page() {
  const [currentStage, setCurrentStage] = useState<DemoStage>('input');
  const [completedStages, setCompletedStages] = useState<DemoStage[]>([]);
  const [requirement, setRequirement] = useState('');
  const [isPlaying, setIsPlaying] = useState(true);
  const [events, setEvents] = useState<EventCard[]>([]);
  const [activeConnections, setActiveConnections] = useState<
    { from: string; to: string }[]
  >([]);
  // Use new V2 network graph with full animation flow
  const [useV2Graph, setUseV2Graph] = useState(true);

  // Ref for interval cleanup to prevent memory leaks
  const negotiationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (negotiationIntervalRef.current) {
        clearInterval(negotiationIntervalRef.current);
      }
    };
  }, []);

  // Timeline events
  const timeline: TimelineEvent[] = useMemo(() => {
    const now = Date.now();
    return completedStages.map((stage, index) => ({
      id: `${stage}-${index}`,
      stage,
      timestamp: now - (completedStages.length - index) * 60000,
      label: stage,
    }));
  }, [completedStages]);

  // Stage navigation
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
    (text: string) => {
      setRequirement(text);
      completeStage('input');
      setCurrentStage('response');
    },
    [completeStage]
  );

  // Stage 2: Start negotiation
  const handleStartNegotiation = useCallback(() => {
    completeStage('response');
    setCurrentStage('negotiation');

    // Clear any existing interval
    if (negotiationIntervalRef.current) {
      clearInterval(negotiationIntervalRef.current);
    }

    // Simulate events appearing
    let eventIndex = 0;
    negotiationIntervalRef.current = setInterval(() => {
      if (eventIndex < MOCK_EVENTS.length) {
        setEvents((prev) => [...prev, MOCK_EVENTS[eventIndex]]);

        // Simulate active connections
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
  }, [completeStage]);

  // Stage 3: Controls
  const handleTogglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const handleSpeedUp = useCallback(() => {
    // Speed up animation
  }, []);

  const handleSkipToResult = useCallback(() => {
    setEvents(MOCK_EVENTS);
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
    setEvents([]);
    setActiveConnections([]);
  }, []);

  const handleShare = useCallback(() => {
    // Share functionality
    alert('分享功能即将上线');
  }, []);

  const handleLearnMore = useCallback(() => {
    window.open('/', '_blank');
  }, []);

  // Render current stage
  const renderStage = () => {
    switch (currentStage) {
      case 'input':
        return <RequirementInput onSubmit={handleSubmitRequirement} />;

      case 'response':
        return useV2Graph ? (
          <NetworkGraphV2
            requirement={requirement}
            agents={MOCK_AGENTS}
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
            agents={MOCK_AGENTS}
            onStartNegotiation={handleStartNegotiation}
          />
        );

      case 'negotiation':
        return (
          <NegotiationLayout
            agents={MOCK_AGENTS}
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
            proposal={MOCK_PROPOSAL}
            onContinue={handleContinueToSummary}
          />
        );

      case 'summary':
        return (
          <SummaryLayout
            timeline={timeline}
            insights={MOCK_INSIGHTS}
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
    </div>
  );
}
