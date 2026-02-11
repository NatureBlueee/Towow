'use client';

import { useState, useRef, useEffect } from 'react';
import type { StoreEvent } from '@/hooks/useStoreWebSocket';

type DevTab = 'state-machine' | 'api-playground' | 'event-log';

interface DeveloperPanelProps {
  negotiationId: string | null;
  phase: string;
  engineState: string;
  events: StoreEvent[];
}

export function DeveloperPanel({
  negotiationId,
  phase,
  engineState,
  events,
}: DeveloperPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<DevTab>('state-machine');

  if (!isOpen) {
    return (
      <div style={{ padding: '0 24px 24px' }}>
        <button
          onClick={() => setIsOpen(true)}
          style={{
            fontSize: 12,
            color: '#999',
            background: 'none',
            border: '1px dashed rgba(0,0,0,0.15)',
            borderRadius: 6,
            padding: '6px 12px',
            cursor: 'pointer',
            width: '100%',
          }}
        >
          Developer Mode
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '0 24px 24px' }}>
      <div
        style={{
          border: '1px solid rgba(0,0,0,0.1)',
          borderRadius: 12,
          backgroundColor: '#fff',
          overflow: 'hidden',
        }}
      >
        {/* Tab bar */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            alignItems: 'center',
          }}
        >
          {(['state-machine', 'api-playground', 'event-log'] as DevTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1,
                padding: '10px 12px',
                fontSize: 12,
                fontWeight: activeTab === tab ? 600 : 400,
                color: activeTab === tab ? '#333' : '#999',
                backgroundColor: activeTab === tab ? 'rgba(0,0,0,0.02)' : 'transparent',
                border: 'none',
                borderBottom: activeTab === tab ? '2px solid #333' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              {tabLabel(tab)}
            </button>
          ))}
          <button
            onClick={() => setIsOpen(false)}
            style={{
              padding: '10px 12px',
              fontSize: 12,
              color: '#999',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>

        {/* Tab content */}
        <div style={{ padding: 16, minHeight: 200 }}>
          {activeTab === 'state-machine' && (
            <StateMachineView engineState={engineState} negotiationId={negotiationId} />
          )}
          {activeTab === 'api-playground' && (
            <ApiPlayground />
          )}
          {activeTab === 'event-log' && (
            <EventLog events={events} />
          )}
        </div>
      </div>
    </div>
  );
}

function tabLabel(tab: DevTab): string {
  const labels: Record<DevTab, string> = {
    'state-machine': 'State Machine',
    'api-playground': 'API Playground',
    'event-log': 'Event Log',
  };
  return labels[tab];
}

// ============ State Machine View ============

const STATE_ORDER = [
  'CREATED', 'FORMULATING', 'FORMULATED', 'ENCODING',
  'OFFERING', 'BARRIER_WAITING', 'SYNTHESIZING', 'COMPLETED',
];

function StateMachineView({
  engineState,
  negotiationId,
}: {
  engineState: string;
  negotiationId: string | null;
}) {
  const currentIdx = STATE_ORDER.indexOf(engineState);

  return (
    <div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>
        {negotiationId ? `Negotiation: ${negotiationId}` : 'No active negotiation'}
      </div>
      {/* State flow */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {STATE_ORDER.map((s, i) => {
          const isCurrent = s === engineState;
          const isPassed = i < currentIdx;
          return (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span
                style={{
                  fontSize: 11,
                  padding: '4px 8px',
                  borderRadius: 4,
                  backgroundColor: isCurrent ? '#D4B8D9' : isPassed ? '#D4F4DD' : 'rgba(0,0,0,0.04)',
                  color: isCurrent ? '#fff' : isPassed ? '#2D7A3F' : '#666',
                  fontWeight: isCurrent ? 600 : 400,
                  fontFamily: 'monospace',
                }}
              >
                {s}
              </span>
              {i < STATE_ORDER.length - 1 && (
                <span style={{ color: '#ccc', fontSize: 10 }}>→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============ API Playground ============

interface PlaygroundSection {
  id: string;
  title: string;
  method: string;
  endpoint: string;
}

const SECTIONS: PlaygroundSection[] = [
  { id: 'list-scenes', title: 'List Scenes', method: 'GET', endpoint: '/store/api/scenes' },
  { id: 'list-agents', title: 'List Agents', method: 'GET', endpoint: '/store/api/agents' },
  { id: 'create-scene', title: 'Create Scene', method: 'POST', endpoint: '/store/api/scenes/register' },
];

const SCENE_TEMPLATES: Record<string, Record<string, string>> = {
  hackathon: {
    scene_id: 'hackathon_custom',
    name: '黑客松组队',
    description: '帮助参赛者找到最佳队友，互补技能快速组队',
    priority_strategy: '技术互补性优先',
    domain_context: '黑客松竞赛场景',
  },
  skill: {
    scene_id: 'skill_exchange_custom',
    name: '技能交换',
    description: '让人们互相教学，用自己的技能交换想学的技能',
    priority_strategy: '双向匹配度优先',
    domain_context: '技能交换与互助学习',
  },
  recruit: {
    scene_id: 'recruit_custom',
    name: '智能招聘',
    description: '帮企业找到合适的人，AI 辅助筛选和匹配',
    priority_strategy: '经验与岗位匹配优先',
    domain_context: '人才招聘与匹配',
  },
};

function ApiPlayground() {
  const [openSection, setOpenSection] = useState<string | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [agentScope, setAgentScope] = useState('all');
  const [sceneForm, setSceneForm] = useState(SCENE_TEMPLATES.hackathon);

  const runRequest = async (id: string, url: string, options?: RequestInit) => {
    setResponses((prev) => ({ ...prev, [id]: '请求中...' }));
    try {
      const resp = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options,
      });
      const data = await resp.json();
      setResponses((prev) => ({
        ...prev,
        [id]: `${resp.status} ${resp.statusText}\n\n${JSON.stringify(data, null, 2)}`,
      }));
    } catch (e) {
      setResponses((prev) => ({
        ...prev,
        [id]: `Error: ${e instanceof Error ? e.message : String(e)}`,
      }));
    }
  };

  return (
    <div style={{ fontSize: 13 }}>
      {/* List Scenes */}
      <PlaygroundCard
        title="GET /store/api/scenes"
        isOpen={openSection === 'list-scenes'}
        onToggle={() => setOpenSection(openSection === 'list-scenes' ? null : 'list-scenes')}
      >
        <button onClick={() => runRequest('list-scenes', '/store/api/scenes')} style={btnStyle}>
          Send
        </button>
        {responses['list-scenes'] && <ResponseBlock text={responses['list-scenes']} />}
      </PlaygroundCard>

      {/* List Agents */}
      <PlaygroundCard
        title="GET /store/api/agents"
        isOpen={openSection === 'list-agents'}
        onToggle={() => setOpenSection(openSection === 'list-agents' ? null : 'list-agents')}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
          <label style={{ fontSize: 12, color: '#666' }}>scope:</label>
          <select
            value={agentScope}
            onChange={(e) => setAgentScope(e.target.value)}
            style={selectStyle}
          >
            <option value="all">all</option>
            <option value="scene:hackathon">scene:hackathon</option>
            <option value="scene:recruitment">scene:recruitment</option>
            <option value="scene:skill_exchange">scene:skill_exchange</option>
            <option value="scene:matchmaking">scene:matchmaking</option>
          </select>
          <button
            onClick={() => runRequest('list-agents', `/store/api/agents?scope=${encodeURIComponent(agentScope)}`)}
            style={btnStyle}
          >
            Send
          </button>
        </div>
        {responses['list-agents'] && <ResponseBlock text={responses['list-agents']} />}
      </PlaygroundCard>

      {/* Create Scene */}
      <PlaygroundCard
        title="POST /store/api/scenes/register"
        isOpen={openSection === 'create-scene'}
        onToggle={() => setOpenSection(openSection === 'create-scene' ? null : 'create-scene')}
      >
        <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
          {Object.keys(SCENE_TEMPLATES).map((key) => (
            <button
              key={key}
              onClick={() => setSceneForm(SCENE_TEMPLATES[key])}
              style={{ ...btnStyle, fontSize: 11, padding: '2px 8px' }}
            >
              {key}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }}>
          {Object.entries(sceneForm).map(([key, value]) => (
            <div key={key} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <label style={{ fontSize: 11, color: '#666', width: 90, flexShrink: 0 }}>{key}:</label>
              <input
                value={value}
                onChange={(e) => setSceneForm((prev) => ({ ...prev, [key]: e.target.value }))}
                style={inputStyle}
              />
            </div>
          ))}
        </div>
        <button
          onClick={() =>
            runRequest('create-scene', '/store/api/scenes/register', {
              method: 'POST',
              body: JSON.stringify(sceneForm),
            })
          }
          style={btnStyle}
        >
          Send
        </button>
        {responses['create-scene'] && <ResponseBlock text={responses['create-scene']} />}
      </PlaygroundCard>
    </div>
  );
}

function PlaygroundCard({
  title,
  isOpen,
  onToggle,
  children,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 8, border: '1px solid rgba(0,0,0,0.06)', borderRadius: 6 }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'monospace',
          fontSize: 12,
          color: '#333',
        }}
      >
        <span>{title}</span>
        <span>{isOpen ? '-' : '+'}</span>
      </button>
      {isOpen && <div style={{ padding: '0 12px 12px' }}>{children}</div>}
    </div>
  );
}

function ResponseBlock({ text }: { text: string }) {
  return (
    <pre
      style={{
        marginTop: 8,
        padding: 8,
        borderRadius: 4,
        backgroundColor: '#F8F6F3',
        fontSize: 11,
        fontFamily: 'monospace',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
        maxHeight: 200,
        overflowY: 'auto',
        color: '#555',
      }}
    >
      {text}
    </pre>
  );
}

const btnStyle: React.CSSProperties = {
  fontSize: 12,
  padding: '4px 12px',
  borderRadius: 4,
  border: '1px solid rgba(0,0,0,0.1)',
  backgroundColor: '#fff',
  color: '#333',
  cursor: 'pointer',
};

const selectStyle: React.CSSProperties = {
  fontSize: 12,
  padding: '3px 8px',
  borderRadius: 4,
  border: '1px solid rgba(0,0,0,0.1)',
  backgroundColor: '#fff',
  fontFamily: 'monospace',
};

const inputStyle: React.CSSProperties = {
  flex: 1,
  fontSize: 12,
  padding: '4px 8px',
  borderRadius: 4,
  border: '1px solid rgba(0,0,0,0.1)',
  fontFamily: 'monospace',
};

// ============ Event Log ============

function EventLog({ events }: { events: StoreEvent[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div style={{ fontSize: 13, color: '#999' }}>
        等待协商事件...
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      style={{
        maxHeight: 400,
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: 12,
      }}
    >
      {events.map((event, i) => (
        <div
          key={i}
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.04)',
          }}
        >
          <div
            onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
            style={{
              padding: '6px 0',
              cursor: 'pointer',
              color: '#555',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <span style={{ color: '#ccc', width: 24 }}>[{i + 1}]</span>
            <span style={{ color: '#D4B8D9', fontWeight: 500 }}>
              {event.event_type}
            </span>
            {event.timestamp && (
              <span style={{ color: '#ccc', marginLeft: 'auto', fontSize: 11 }}>
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
          {expandedIdx === i && (
            <pre
              style={{
                padding: '6px 0 6px 28px',
                fontSize: 11,
                color: '#666',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {JSON.stringify(event.data || event, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
