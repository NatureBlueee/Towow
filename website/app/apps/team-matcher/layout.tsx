import { ReactNode } from 'react';
import type { Metadata } from 'next';
// [MAINTENANCE MODE] TeamAuthProvider disabled — it calls getCurrentUser which requires backend
// import { TeamAuthProvider } from '@/context/TeamAuthContext';

export const metadata: Metadata = {
  title: 'Team Matcher - ToWow',
  description: '发出信号，找到共振的伙伴，组建最佳团队',
};

/**
 * Team Matcher layout.
 *
 * [MAINTENANCE MODE] TeamAuthProvider temporarily removed to avoid backend calls.
 * To restore: uncomment TeamAuthProvider import and wrap children with it.
 */
export default function TeamLayout({ children }: { children: ReactNode }) {
  // return <TeamAuthProvider>{children}</TeamAuthProvider>;
  return <>{children}</>;
}
