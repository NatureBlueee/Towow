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

// ============ Data extraction helpers ============

/** Strip Markdown syntax, return clean plain text for card display. */
function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^[-*]\s+/gm, '')
    .replace(/^\d+[.)]\s+/gm, '')
    .replace(/\n{2,}/g, ' ')
    .replace(/\n/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/** Get clean bio text for card — prefers self_introduction, falls back to bio with Markdown stripped. */
function getCardBio(agent: StoreAgent): string {
  if (agent.self_introduction && typeof agent.self_introduction === 'string' && agent.self_introduction.trim()) {
    return stripMarkdown(agent.self_introduction);
  }
  if (agent.bio) {
    return stripMarkdown(agent.bio);
  }
  return '';
}

/** Extract tag names from SecondMe shades. */
function getShadesTags(agent: StoreAgent): string[] {
  const shades = agent.shades;
  if (!shades || shades.length === 0) return [];
  return shades.slice(0, 3).map(s => s.name || s.description || '').filter(Boolean);
}

/** Avatar with real image support + initial-circle fallback. */
function AgentAvatar({ agent, size, fallbackColor }: {
  agent: StoreAgent;
  size: number;
  fallbackColor: string;
}) {
  const [imgError, setImgError] = useState(false);

  if (agent.avatar && !imgError) {
    return (
      <img
        src={agent.avatar}
        alt={agent.display_name}
        onError={() => setImgError(true)}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          objectFit: 'cover',
          flexShrink: 0,
        }}
      />
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: fallbackColor,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: Math.round(size * 0.4),
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {getInitial(agent.display_name)}
    </div>
  );
}

function AgentCard({ agent, scope, cardTemplate }: {
  agent: StoreAgent;
  scope: string;
  cardTemplate: 'hackathon' | 'default';
}) {
  const config = getDisplayConfig(scope);
  const avatarColor = getAvatarColor(agent, scope);
  const sourceColor = SOURCE_COLORS[agent.source] || SOURCE_COLORS.default;
  const sceneTags = config.tagSource(agent);
  const tags = sceneTags.length > 0 ? sceneTags : getShadesTags(agent);
  const highlight = config.highlight(agent);
  const cardBio = getCardBio(agent);

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
        <AgentAvatar agent={agent} size={36} fallbackColor={avatarColor} />
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

      {/* Tags: scene-specific skills or SecondMe shades */}
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

      {/* Bio summary — Markdown stripped, clean text */}
      {cardBio && !highlight && (
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
          {cardBio}
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
  const shadesTags = getShadesTags(agent);
  const techTags = skills.length > 0 ? skills : shadesTags;
  const hackathonHistory = agent.hackathon_history as string | undefined;
  const availability = agent.availability as string | undefined;
  const cardBio = getCardBio(agent);

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
        <AgentAvatar agent={agent} size={40} fallbackColor={avatarColor} />
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

      {/* Tech stack / shades tags */}
      {techTags.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>
            {skills.length > 0 ? '技术栈' : '兴趣'}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {techTags.map((tag) => (
              <span
                key={tag}
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 4,
                  backgroundColor: '#FFF8F0',
                  color: '#E88A5C',
                  fontWeight: 500,
                }}
              >
                {tag}
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

      {/* Bio — Markdown stripped */}
      {cardBio && (
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
          {cardBio}
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
