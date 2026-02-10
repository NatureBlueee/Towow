/**
 * Negotiation API client.
 *
 * Standalone module for all negotiation REST endpoints.
 * Base URL defaults to /v1 (proxied via Next.js rewrites) and can be
 * overridden via NEXT_PUBLIC_NEGOTIATION_API_URL.
 */

import type {
  SubmitDemandRequest,
  SubmitDemandResponse,
  ConfirmFormulationRequest,
  UserActionRequest,
} from '@/types/negotiation';

const API_BASE =
  process.env.NEXT_PUBLIC_NEGOTIATION_API_URL || '/v1';

// ============ Generic request helper ============

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

// ============ Scene endpoints ============

/**
 * Create a new scene.
 */
export async function createScene(params: {
  scene_id?: string;
  name: string;
  description?: string;
}): Promise<{ scene_id: string }> {
  return request('/api/scenes', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Register an agent into a scene.
 */
export async function registerAgent(
  sceneId: string,
  params: { agent_id: string; display_name: string; capabilities?: string[] },
): Promise<{ ok: boolean }> {
  return request(`/api/scenes/${sceneId}/agents`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

// ============ Negotiation endpoints ============

/**
 * Submit a demand to start a negotiation.
 * Returns the newly created negotiation ID.
 */
export async function submitDemand(
  sceneId: string,
  userId: string,
  intent: string,
): Promise<string> {
  const body: SubmitDemandRequest = { scene_id: sceneId, user_id: userId, intent };
  const data = await request<SubmitDemandResponse>('/api/negotiations/submit', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return data.negotiation_id;
}

/**
 * Confirm the formulated demand text.
 */
export async function confirmFormulation(
  negotiationId: string,
  formulatedText: string,
): Promise<void> {
  const body: ConfirmFormulationRequest = { confirmed_text: formulatedText };
  await request(`/api/negotiations/${negotiationId}/confirm`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Perform a user action on a negotiation (accept, modify, reject, cancel).
 */
export async function userAction(
  negotiationId: string,
  action: UserActionRequest['action'],
  payload?: Record<string, unknown>,
): Promise<void> {
  const body: UserActionRequest = { action, payload };
  await request(`/api/negotiations/${negotiationId}/action`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Get current negotiation status (polling fallback).
 */
export async function getNegotiationStatus(
  negotiationId: string,
): Promise<Record<string, unknown>> {
  return request(`/api/negotiations/${negotiationId}`, { method: 'GET' });
}

// ============ WebSocket URL helper ============

const WS_BASE =
  process.env.NEXT_PUBLIC_NEGOTIATION_WS_URL || 'ws://localhost:8080/v1';

/**
 * Build the WebSocket URL for a negotiation event stream.
 */
export function getWebSocketUrl(negotiationId: string): string {
  return `${WS_BASE}/ws/negotiation/${negotiationId}`;
}
