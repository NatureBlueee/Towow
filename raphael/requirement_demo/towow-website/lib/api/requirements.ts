import { RequirementInput, Requirement } from '@/types/experience';

// 使用相对路径，通过 Next.js rewrites 代理到后端
const API_BASE = '';

export interface NegotiationResult {
  requirement_id: string;
  status: 'completed' | 'failed' | 'timeout';
  summary: string;
  participants: Array<{
    agent_id: string;
    agent_name: string;
    contribution: string;
  }>;
  final_proposal?: string;
  created_at: string;
}

export async function submitRequirement(
  data: RequirementInput,
  submitterId?: string
): Promise<Requirement> {
  const response = await fetch(`${API_BASE}/api/requirements`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      title: data.title,
      description: data.description,
      submitter_id: submitterId,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to submit requirement');
  }

  const result = await response.json();

  return {
    requirement_id: result.requirement_id,
    channel_id: result.channel_id || '',
    requirement_text: result.description,
    priority: 'normal',
    status: result.status,
    created_at: result.created_at,
  };
}

export async function getRequirement(id: string): Promise<Requirement> {
  const response = await fetch(`${API_BASE}/api/requirements/${id}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch requirement');
  }

  const result = await response.json();

  return {
    requirement_id: result.requirement_id,
    channel_id: result.channel_id || '',
    requirement_text: result.description,
    priority: 'normal',
    status: result.status,
    created_at: result.created_at,
  };
}

export async function getNegotiationResult(
  requirementId: string
): Promise<NegotiationResult | null> {
  const response = await fetch(
    `${API_BASE}/api/requirements/${requirementId}`,
    { credentials: 'include' }
  );

  if (!response.ok) {
    return null;
  }

  const result = await response.json();

  if (result.status !== 'completed' && result.status !== 'failed') {
    return null;
  }

  return {
    requirement_id: result.requirement_id,
    status: result.status as 'completed' | 'failed' | 'timeout',
    summary: result.metadata?.summary || 'Negotiation completed',
    participants: result.metadata?.participants || [],
    final_proposal: result.metadata?.final_proposal,
    created_at: result.created_at,
  };
}
