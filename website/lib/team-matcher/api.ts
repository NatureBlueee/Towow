// lib/team-matcher/api.ts
// Team Matcher API client

import {
  TeamRequest,
  TeamRequestDetail,
  TeamRequestListItem,
  TeamRequestFormData,
  CreateRequestResponse,
  ProposalsResponse,
  TeamProposal,
  RoleCoverage,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Submit a new team matching request.
 */
export async function createTeamRequest(
  data: TeamRequestFormData & { user_id: string }
): Promise<CreateRequestResponse> {
  const res = await fetch(`${API_BASE}/api/team/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

/**
 * Submit an offer (participation intent) for a team request.
 * Matches backend MatchOfferCreateRequest model.
 */
export async function submitTeamOffer(offer: {
  request_id: string;
  agent_id: string;
  agent_name: string;
  role: string;
  skills: string[];
  specialties: string[];
  motivation: string;
  availability: string;
}): Promise<{ offer_id: string }> {
  const res = await fetch(`${API_BASE}/api/team/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(offer),
  });
  if (!res.ok) throw new Error(`Failed to submit offer (HTTP ${res.status})`);
  return await res.json();
}

/**
 * Get the full details of a team request (matches backend TeamRequestResponse).
 */
export async function getTeamRequest(requestId: string): Promise<TeamRequestDetail> {
  const res = await fetch(`${API_BASE}/api/team/request/${requestId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

/**
 * List all team requests, optionally filtered by status.
 */
export async function getTeamRequests(
  status?: string
): Promise<TeamRequestListItem[]> {
  const url = new URL(`${API_BASE}/api/team/requests`, window.location.origin);
  if (status) {
    url.searchParams.set('status', status);
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

/**
 * Get generated proposals for a request.
 * Maps backend TeamProposalResponse to frontend TeamProposal shape.
 */
export async function getTeamProposals(
  requestId: string
): Promise<ProposalsResponse> {
  const res = await fetch(
    `${API_BASE}/api/team/request/${requestId}/proposals`
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch proposals (HTTP ${res.status})`);
  }
  // Backend returns List[TeamProposalResponse] (plain array)
  const data = await res.json();
  const rawProposals: RawProposalResponse[] = Array.isArray(data)
    ? data
    : data.proposals || [];

  const proposals: TeamProposal[] = rawProposals.map((raw, index) => {
    const typeKey = inferProposalType(index);
    return {
      proposal_id: raw.proposal_id,
      proposal_type: typeKey,
      proposal_label: raw.title,
      proposal_description: raw.reasoning || '',
      coverage_score: raw.coverage_score ?? 0,
      synergy_score: raw.synergy_score ?? 0,
      team_members: (raw.members || []).map((m) => ({
        agent_id: m.agent_id,
        agent_name: m.agent_name,
        avatar_url: undefined,
        role: m.role,
        skills: m.skills || [],
        brief_intro: m.contribution || '',
        match_reason: m.contribution || '',
      })),
      role_coverage: buildRoleCoverage(raw.members || []),
      unexpected_combinations: raw.unexpected_combinations || [],
    };
  });

  return {
    request_id: requestId,
    proposals,
    generated_at: new Date().toISOString(),
  };
}

// ============ SecondMe Form Suggestions ============

export interface FormSuggestions {
  project_idea: string;
  skills: string[];
  availability: string;
  roles_needed: string[];
}

export interface FormSuggestResponse {
  success: boolean;
  message: string;
  suggestions: FormSuggestions | null;
  error: string | null;
}

/**
 * Ask SecondMe to suggest form field values based on user's profile.
 * Requires authenticated session (cookie). Never throws — returns
 * {success: false} on any error so the form can gracefully fall back.
 */
export async function getFormSuggestions(): Promise<FormSuggestResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/team/suggest`, {
      credentials: 'include',
    });
    if (res.status === 401) {
      return { success: false, message: '', suggestions: null, error: 'not_authenticated' };
    }
    if (!res.ok) {
      return { success: false, message: '无法获取建议', suggestions: null, error: `http_${res.status}` };
    }
    return await res.json();
  } catch {
    return { success: false, message: '网络请求失败', suggestions: null, error: 'network_error' };
  }
}

// ============ Internal helpers ============

/** Raw member shape from the backend */
interface RawMember {
  agent_id: string;
  agent_name: string;
  role: string;
  skills?: string[];
  contribution?: string;
}

/** Raw proposal shape from the backend */
interface RawProposalResponse {
  proposal_id: string;
  title: string;
  members: RawMember[];
  coverage_score?: number;
  synergy_score?: number;
  unexpected_combinations?: string[];
  reasoning?: string;
}

/** Infer a proposal type label from its position in the list */
function inferProposalType(index: number): TeamProposal['proposal_type'] {
  const types: TeamProposal['proposal_type'][] = [
    'fast_validation',
    'tech_depth',
    'cross_innovation',
  ];
  return types[index % types.length];
}

/** Build role coverage entries from member list */
function buildRoleCoverage(members: RawMember[]): RoleCoverage[] {
  const seen = new Map<string, string>();
  for (const m of members) {
    if (m.role && !seen.has(m.role)) {
      seen.set(m.role, m.agent_name);
    }
  }
  return Array.from(seen.entries()).map(([role, coveredBy]) => ({
    role,
    status: 'covered' as const,
    covered_by: coveredBy,
  }));
}
