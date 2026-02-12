'use client';

import { useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_NEGOTIATION_API_URL || '/v1';

interface ApiState {
  loading: boolean;
  error: string | null;
}

export interface UseNegotiationApiReturn {
  submitDemand: (sceneId: string, userId: string, intent: string, kStar?: number, minScore?: number) => Promise<string>;
  confirmFormulation: (negotiationId: string, formulatedText: string) => Promise<void>;
  userAction: (
    negotiationId: string,
    action: 'accept' | 'modify' | 'reject' | 'cancel',
    payload?: Record<string, unknown>,
  ) => Promise<void>;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

export function useNegotiationApi(): UseNegotiationApiReturn {
  const [apiState, setApiState] = useState<ApiState>({ loading: false, error: null });

  const request = useCallback(async <T>(
    path: string,
    body: Record<string, unknown>,
  ): Promise<T> => {
    setApiState({ loading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed: ${res.status}`);
      }
      const data = await res.json();
      setApiState({ loading: false, error: null });
      return data as T;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setApiState({ loading: false, error: message });
      throw err;
    }
  }, []);

  const submitDemand = useCallback(
    async (sceneId: string, userId: string, intent: string, kStar?: number, minScore?: number): Promise<string> => {
      const body: Record<string, unknown> = { scene_id: sceneId, user_id: userId, intent };
      if (kStar !== undefined) body.k_star = kStar;
      if (minScore !== undefined) body.min_score = minScore;
      const data = await request<{ negotiation_id: string }>(
        '/api/negotiations/submit',
        body,
      );
      return data.negotiation_id;
    },
    [request],
  );

  const confirmFormulation = useCallback(
    async (negotiationId: string, formulatedText: string): Promise<void> => {
      await request(`/api/negotiations/${negotiationId}/confirm`, {
        confirmed_text: formulatedText,
      });
    },
    [request],
  );

  const userAction = useCallback(
    async (
      negotiationId: string,
      action: 'accept' | 'modify' | 'reject' | 'cancel',
      payload?: Record<string, unknown>,
    ): Promise<void> => {
      await request(`/api/negotiations/${negotiationId}/action`, {
        action,
        payload,
      });
    },
    [request],
  );

  const clearError = useCallback(() => {
    setApiState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    submitDemand,
    confirmFormulation,
    userAction,
    loading: apiState.loading,
    error: apiState.error,
    clearError,
  };
}
