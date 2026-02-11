'use client';

import { useState, useMemo } from 'react';
import {
  computeTopologyLayout,
  type TaskNode,
  type LayoutNode,
} from '@/lib/topology-layout';

interface Participant {
  agent_id: string;
  display_name: string;
  role_in_plan: string;
}

interface PlanTask {
  id: string;
  title: string;
  description?: string;
  assignee_id: string;
  prerequisites: string[];
  status?: string;
}

export interface TopologyViewProps {
  planJson: {
    summary?: string;
    participants: Participant[];
    tasks: PlanTask[];
    topology?: { edges: Array<{ from: string; to: string }> };
  };
}

const NODE_W = 160;
const NODE_H = 70;
const PAD = 20;

/** Deterministic color from string hash */
function hashColor(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  const hue = ((h % 360) + 360) % 360;
  return `hsl(${hue}, 55%, 55%)`;
}

export function TopologyView({ planJson }: TopologyViewProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const taskNodes: TaskNode[] = useMemo(
    () =>
      planJson.tasks.map((t) => ({
        id: t.id,
        title: t.title,
        assigneeId: t.assignee_id,
        prerequisites: t.prerequisites,
      })),
    [planJson.tasks],
  );

  const layout = useMemo(
    () => computeTopologyLayout(taskNodes, 200, 90),
    [taskNodes],
  );

  if (!layout) return null;

  const nodeMap = new Map<string, LayoutNode>(layout.nodes.map((n) => [n.id, n]));
  const taskMap = new Map(planJson.tasks.map((t) => [t.id, t]));
  const partMap = new Map(planJson.participants.map((p) => [p.agent_id, p]));

  // Build adjacency sets for highlight
  const upstream = new Map<string, Set<string>>();
  const downstream = new Map<string, Set<string>>();
  for (const n of layout.nodes) {
    upstream.set(n.id, new Set());
    downstream.set(n.id, new Set());
  }
  for (const e of layout.edges) {
    downstream.get(e.from)?.add(e.to);
    upstream.get(e.to)?.add(e.from);
  }

  const related = new Set<string>();
  if (selected) {
    related.add(selected);
    upstream.get(selected)?.forEach((id) => related.add(id));
    downstream.get(selected)?.forEach((id) => related.add(id));
  }

  const svgW = layout.width + NODE_W + PAD * 2;
  const svgH = layout.height + NODE_H + PAD * 2;

  const selectedTask = selected ? taskMap.get(selected) : null;
  const selectedNode = selected ? nodeMap.get(selected) : null;

  return (
    <div style={{ overflowX: 'auto', margin: '12px 0' }}>
      <svg
        width={svgW}
        height={svgH + (selectedTask ? 100 : 0)}
        style={{ display: 'block' }}
        onClick={(e) => {
          if ((e.target as SVGElement).tagName === 'svg') setSelected(null);
        }}
      >
        {/* Edges */}
        {layout.edges.map((e) => {
          const src = nodeMap.get(e.from);
          const dst = nodeMap.get(e.to);
          if (!src || !dst) return null;
          const x1 = src.x + PAD + NODE_W;
          const y1 = src.y + PAD + NODE_H / 2;
          const x2 = dst.x + PAD;
          const y2 = dst.y + PAD + NODE_H / 2;
          const mx = (x1 + x2) / 2;
          const isHighlighted =
            selected && related.has(e.from) && related.has(e.to);
          const dimmed = selected && !isHighlighted;
          return (
            <path
              key={`${e.from}-${e.to}`}
              d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
              fill="none"
              stroke={isHighlighted ? '#5B8DEF' : '#D0D0D0'}
              strokeWidth={isHighlighted ? 2 : 1.5}
              opacity={dimmed ? 0.3 : 1}
            />
          );
        })}

        {/* Nodes */}
        {layout.nodes.map((n) => {
          const task = taskMap.get(n.id);
          const assignee = task ? partMap.get(task.assignee_id) : null;
          const color = hashColor(n.assigneeId);
          const initial = (assignee?.display_name || n.assigneeId)[0]?.toUpperCase() || '?';
          const isSelected = selected === n.id;
          const dimmed = selected && !related.has(n.id);
          const nx = n.x + PAD;
          const ny = n.y + PAD;

          return (
            <g
              key={n.id}
              transform={`translate(${nx},${ny})`}
              style={{ cursor: 'pointer', opacity: dimmed ? 0.3 : 1 }}
              onClick={(e) => {
                e.stopPropagation();
                setSelected(selected === n.id ? null : n.id);
              }}
            >
              <rect
                width={NODE_W}
                height={NODE_H}
                rx={8}
                fill="#fff"
                stroke={isSelected ? '#5B8DEF' : 'rgba(0,0,0,0.08)'}
                strokeWidth={isSelected ? 2 : 1}
                filter="url(#shadow)"
              />
              {/* Avatar circle */}
              <circle cx={24} cy={NODE_H / 2} r={14} fill={color} />
              <text
                x={24}
                y={NODE_H / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#fff"
                fontSize={12}
                fontWeight={600}
              >
                {initial}
              </text>
              {/* Title */}
              <text
                x={46}
                y={26}
                fontSize={12}
                fontWeight={500}
                fill="#333"
              >
                {n.title.length > 12 ? n.title.slice(0, 12) + '...' : n.title}
              </text>
              {/* Assignee name */}
              <text x={46} y={48} fontSize={11} fill="#999">
                {assignee?.display_name || n.assigneeId}
              </text>
            </g>
          );
        })}

        {/* Detail panel */}
        {selectedTask && selectedNode && (
          <foreignObject
            x={selectedNode.x + PAD}
            y={selectedNode.y + PAD + NODE_H + 8}
            width={260}
            height={90}
          >
            <div
              style={{
                background: '#fff',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 12,
                lineHeight: 1.6,
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              }}
            >
              {selectedTask.description && (
                <div style={{ color: '#555', marginBottom: 4 }}>
                  {selectedTask.description}
                </div>
              )}
              <div style={{ color: '#999' }}>
                {partMap.get(selectedTask.assignee_id)?.role_in_plan}
              </div>
              {selectedTask.prerequisites.length > 0 && (
                <div style={{ color: '#bbb', marginTop: 2 }}>
                  前置: {selectedTask.prerequisites.join(', ')}
                </div>
              )}
            </div>
          </foreignObject>
        )}

        {/* Shadow filter */}
        <defs>
          <filter id="shadow" x="-4%" y="-4%" width="108%" height="116%">
            <feDropShadow dx="0" dy="1" stdDeviation="3" floodOpacity="0.08" />
          </filter>
        </defs>
      </svg>
    </div>
  );
}
