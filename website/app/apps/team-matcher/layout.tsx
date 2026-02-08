import { ReactNode } from 'react';
import type { Metadata } from 'next';
import { TeamAuthProvider } from '@/context/TeamAuthContext';

export const metadata: Metadata = {
  title: 'Team Matcher - ToWow',
  description: '发出信号，找到共振的伙伴，组建最佳团队',
};

/**
 * Team Matcher layout with optional authentication.
 *
 * TeamAuthProvider silently checks if the user is logged in and makes
 * the agent_id available for WebSocket connections. If the user is NOT
 * logged in, pages still render normally in mock mode.
 */
export default function TeamLayout({ children }: { children: ReactNode }) {
  return <TeamAuthProvider>{children}</TeamAuthProvider>;
}
