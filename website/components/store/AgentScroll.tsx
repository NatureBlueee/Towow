'use client';

import { useState, useEffect } from 'react';
import { getAgents, type StoreAgent } from '@/lib/store-api';

interface AgentScrollProps {
  scope: string;
  cardTemplate?: 'hackathon' | 'default';
}

// ============ Scene-specific display configuration ============
// Mirrors SCENE_DISPLAY from app.js: each scene highlights different agent fields

type HighlightFn = (agent: StoreAgent) => string;
type TagSourceFn = (agent: StoreAgent) => string[];

interface SceneDisplayConfig {
  color: string;
  highlight: HighlightFn;
  tagSource: TagSourceFn;
}

const SCENE_DISPLAY: Record<string, SceneDisplayConfig> = {
  hackathon: {
    color: '#F9A87C',
    highlight: (a) => {
      const parts: string[] = [];
      if (a.hackathon_history) parts.push(String(a.hackathon_history));
      if (a.availability) parts.push(String(a.availability));
      return parts.join(' \u00B7 ');
    },
    tagSource: (a) => (a.skills || []).slice(0, 3),
  },
  recruitment: {
    color: '#8FD5A3',
    highlight: (a) => {
      const parts: string[] = [];
      if (a.experience_years) parts.push(`${a.experience_years}年经验`);
      if (a.expected_salary) parts.push(String(a.expected_salary));
      if (a.location) parts.push(String(a.location));
      return parts.join(' \u00B7 ');
    },
    tagSource: (a) => {
      const tags = (a.skills || []).slice(0, 2);
      const highlights = a.highlights as string[] | undefined;
      if (highlights && highlights.length > 0) tags.push(highlights[0]);
      return tags.slice(0, 3);
    },
  },
  skill_exchange: {
    color: '#FFE4B5',
    highlight: (a) => {
      const parts: string[] = [];
      if (a.price_range) parts.push(String(a.price_range));
      if (a.availability) parts.push(String(a.availability));
      if (a.teaching_style) parts.push(String(a.teaching_style));
      return parts.join(' \u00B7 ');
    },
    tagSource: (a) => (a.skills || []).slice(0, 3),
  },
  matchmaking: {
    color: '#D4B8D9',
    highlight: (a) => {
      const parts: string[] = [];
      if (a.age) parts.push(`${a.age}岁`);
      if (a.personality) parts.push(String(a.personality));
      if (a.location) parts.push(String(a.location));
      return parts.join(' \u00B7 ');
    },
    tagSource: (a) => ((a.values as string[]) || []).slice(0, 3),
  },
};

const DEFAULT_DISPLAY: SceneDisplayConfig = {
  color: '#8FD5A3',
  highlight: (a) => {
    if (a.experience) return String(a.experience);
    if (a.location) return String(a.location);
    return '';
  },
  tagSource: (a) => (a.skills || []).slice(0, 3),
};

const SOURCE_COLORS: Record<string, string> = {
  secondme: '#F9A87C',
  json_file: '#C4A0CA',
  default: '#8FD5A3',
};

function getSceneIdFromScope(scope: string): string | null {
  if (scope.startsWith('scene:')) return scope.slice(6);
  return null;
}

function getDisplayConfig(scope: string): SceneDisplayConfig {
  const sid = getSceneIdFromScope(scope);
  return (sid && SCENE_DISPLAY[sid]) || DEFAULT_DISPLAY;
}

function getInitial(name: string): string {
  return name.charAt(0).toUpperCase();
}

function getAvatarColor(agent: StoreAgent, scope: string): string {
  const sid = getSceneIdFromScope(scope);
  if (sid && SCENE_DISPLAY[sid]) return SCENE_DISPLAY[sid].color;
  const source = agent.source || '';
  if (source.toLowerCase().includes('secondme')) return SOURCE_COLORS.secondme;
  if (source.toLowerCase().includes('json')) return SOURCE_COLORS.json_file;
  return SOURCE_COLORS.default;
}

function AgentCard({ agent, scope, cardTemplate }: {
  agent: StoreAgent;
  scope: string;
  cardTemplate: 'hackathon' | 'default';
}) {
  const config = getDisplayConfig(scope);
  const avatarColor = getAvatarColor(agent, scope);
  const sourceColor = SOURCE_COLORS[agent.source] || SOURCE_COLORS.default;
  const tags = config.tagSource(agent);
  const highlight = config.highlight(agent);

  if (cardTemplate === 'hackathon') {
    return <HackathonAgentCard agent={agent} avatarColor={avatarColor} sourceColor={sourceColor} />;
  }

  return (
    <div
      style={{
        minWidth: 160,
        padding: '16px',
        borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        backgroundColor: '#fff',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            backgroundColor: avatarColor,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 15,
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          {getInitial(agent.display_name)}
        </div>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {agent.display_name}
          </div>
          <div
            style={{
              fontSize: 11,
              color: sourceColor,
              fontWeight: 500,
            }}
          >
            {agent.source}
          </div>
        </div>
      </div>

      {/* Scene-specific highlight line */}
      {highlight && (
        <div
          style={{
            fontSize: 12,
            color: '#666',
            lineHeight: 1.4,
          }}
        >
          {highlight}
        </div>
      )}

      {/* Bio fallback (when no scene-specific highlight) */}
      {!highlight && agent.bio && (
        <div
          style={{
            fontSize: 12,
            color: '#666',
            lineHeight: 1.4,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {agent.bio}
        </div>
      )}

      {tags.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {tags.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: 11,
                padding: '2px 6px',
                borderRadius: 4,
                backgroundColor: 'rgba(0,0,0,0.04)',
                color: '#555',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ============ Hackathon-specific card ============
// Emphasizes: tech stack, hackathon experience, time availability

function HackathonAgentCard({
  agent,
  avatarColor,
  sourceColor,
}: {
  agent: StoreAgent;
  avatarColor: string;
  sourceColor: string;
}) {
  const skills = (agent.skills || []).slice(0, 4);
  const hackathonHistory = agent.hackathon_history as string | undefined;
  const availability = agent.availability as string | undefined;

  return (
    <div
      style={{
        minWidth: 200,
        padding: '16px',
        borderRadius: 12,
        border: '1px solid rgba(0,0,0,0.06)',
        backgroundColor: '#fff',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        borderLeft: `3px solid #F9A87C`,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            backgroundColor: avatarColor,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          {getInitial(agent.display_name)}
        </div>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {agent.display_name}
          </div>
          <div style={{ fontSize: 11, color: sourceColor, fontWeight: 500 }}>
            {agent.source}
          </div>
        </div>
      </div>

      {/* Tech stack */}
      {skills.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>技术栈</div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {skills.map((skill) => (
              <span
                key={skill}
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 4,
                  backgroundColor: '#FFF8F0',
                  color: '#E88A5C',
                  fontWeight: 500,
                }}
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Hackathon experience + availability */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {hackathonHistory && (
          <div
            style={{
              fontSize: 11,
              padding: '3px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(0,0,0,0.03)',
              color: '#666',
            }}
          >
            {hackathonHistory}
          </div>
        )}
        {availability && (
          <div
            style={{
              fontSize: 11,
              padding: '3px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(0,0,0,0.03)',
              color: '#666',
            }}
          >
            {availability}
          </div>
        )}
      </div>

      {/* Bio */}
      {agent.bio && (
        <div
          style={{
            fontSize: 12,
            color: '#666',
            lineHeight: 1.4,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {agent.bio}
        </div>
      )}
    </div>
  );
}

export function AgentScroll({ scope, cardTemplate = 'default' }: AgentScrollProps) {
  const [agents, setAgents] = useState<StoreAgent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getAgents(scope)
      .then((data) => {
        if (!cancelled) setAgents(data.agents);
      })
      .catch(() => {
        if (!cancelled) setAgents([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [scope]);

  if (loading) {
    return (
      <div style={{ padding: '16px 24px', color: '#999', fontSize: 14 }}>
        加载 Agent 中...
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div style={{ padding: '16px 24px', color: '#999', fontSize: 14 }}>
        当前范围内暂无 Agent
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        padding: '0 24px 16px',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      {agents.map((agent) => (
        <AgentCard key={agent.agent_id} agent={agent} scope={scope} cardTemplate={cardTemplate} />
      ))}
    </div>
  );
}
