/**
 * Store API client.
 *
 * All endpoints hit /store/api/* which Next.js rewrites to Railway.
 */

const API_BASE = '/store';

// ============ Generic request helper ============

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    credentials: 'include',
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ============ Types ============

export interface StoreNetworkInfo {
  name: string;
  version: string;
  total_agents: number;
  total_scenes: number;
  scenes: StoreScene[];
  secondme_enabled: boolean;
}

export interface StoreScene {
  scene_id: string;
  name: string;
  description: string;
  agent_count: number;
}

export interface StoreAgent {
  agent_id: string;
  display_name: string;
  source: string;
  scene_ids: string[];
  skills?: string[];
  bio?: string;
  [key: string]: unknown;
}

export interface StoreNegotiation {
  negotiation_id: string;
  state: string;
  demand_raw: string;
  demand_formulated: string | null;
  participants: StoreParticipant[];
  plan_output: string | null;
  plan_json: Record<string, unknown> | null;
  center_rounds: number;
  scope: string;
  agent_count: number;
}

export interface StoreParticipant {
  agent_id: string;
  display_name: string;
  resonance_score: number;
  state: string;
  offer_content?: string;
  source?: string;
  scene_ids?: string[];
}

// ============ Network info ============

export async function getNetworkInfo(): Promise<StoreNetworkInfo> {
  return request('/api/info', { method: 'GET' });
}

// ============ Agents ============

export async function getAgents(scope = 'all'): Promise<{
  agents: StoreAgent[];
  count: number;
  scope: string;
}> {
  return request(`/api/agents?scope=${encodeURIComponent(scope)}`, {
    method: 'GET',
  });
}

// ============ Scenes ============

export async function getScenes(): Promise<{ scenes: StoreScene[] }> {
  return request('/api/scenes', { method: 'GET' });
}

// ============ Negotiation ============

export async function startNegotiation(params: {
  intent: string;
  user_id?: string;
  scope?: string;
}): Promise<StoreNegotiation> {
  return request('/api/negotiate', {
    method: 'POST',
    body: JSON.stringify({
      intent: params.intent,
      user_id: params.user_id || 'anonymous',
      scope: params.scope || 'all',
    }),
  });
}

export async function getNegotiation(
  negId: string,
): Promise<StoreNegotiation> {
  return request(`/api/negotiate/${negId}`, { method: 'GET' });
}

export async function confirmNegotiation(negId: string): Promise<void> {
  await request(`/api/negotiate/${negId}/confirm`, { method: 'POST' });
}

// ============ SecondMe 辅助需求 ============

export async function assistDemand(params: {
  mode: 'polish' | 'surprise';
  scene_id?: string;
  raw_text?: string;
}): Promise<{ demand_text: string; mode: string }> {
  return request('/api/assist-demand', {
    method: 'POST',
    body: JSON.stringify({
      mode: params.mode,
      scene_id: params.scene_id || '',
      raw_text: params.raw_text || '',
    }),
  });
}

// ============ WebSocket URL ============

export function getStoreWebSocketUrl(negId: string): string {
  // Vercel rewrites only proxy HTTP, not WebSocket.
  // In production, connect directly to the backend.
  const wsBackend = process.env.NEXT_PUBLIC_WS_BACKEND_URL;
  if (wsBackend) {
    return `${wsBackend}/store/ws/${negId}`;
  }
  // Local dev: connect directly to backend on port 8080
  return `ws://localhost:8080/store/ws/${negId}`;
}
