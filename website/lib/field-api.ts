/**
 * V2 Intent Field API client.
 *
 * Endpoints hit /field/api/* which Next.js rewrites to backend.
 */

const API_BASE = '/field';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ============ Types ============

export interface FieldStats {
  intent_count: number;
  owner_count: number;
}

export interface MatchResultItem {
  intent_id: string;
  score: number;
  owner: string;
  text: string;
  metadata: Record<string, unknown>;
}

export interface MatchResponse {
  results: MatchResultItem[];
  query_time_ms: number;
  total_intents: number;
}

export interface OwnerMatchItem {
  owner: string;
  score: number;
  top_intents: MatchResultItem[];
}

export interface OwnerMatchResponse {
  results: OwnerMatchItem[];
  query_time_ms: number;
  total_intents: number;
  total_owners: number;
}

export interface DepositResponse {
  intent_id: string;
  message: string;
}

export interface LoadProfilesResponse {
  loaded: number;
  total_intents: number;
  total_owners: number;
  message: string;
}

// ============ API functions ============

export async function getFieldStats(): Promise<FieldStats> {
  return request('/api/stats');
}

export async function depositIntent(
  text: string,
  owner: string,
  metadata: Record<string, unknown> = {},
): Promise<DepositResponse> {
  return request('/api/deposit', {
    method: 'POST',
    body: JSON.stringify({ text, owner, metadata }),
  });
}

export async function matchIntents(
  text: string,
  k: number = 10,
): Promise<MatchResponse> {
  return request('/api/match', {
    method: 'POST',
    body: JSON.stringify({ text, k }),
  });
}

export async function matchOwners(
  text: string,
  k: number = 10,
): Promise<OwnerMatchResponse> {
  return request('/api/match-owners', {
    method: 'POST',
    body: JSON.stringify({ text, k }),
  });
}

export async function loadProfiles(): Promise<LoadProfilesResponse> {
  return request('/api/load-profiles', { method: 'POST' });
}
