'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getCurrentUser } from '@/lib/api/auth';

/**
 * Lightweight auth context for Team Matcher.
 *
 * Unlike the full ExperienceProvider + useAuth pattern used by demand-negotiation,
 * this context:
 *  - Never blocks rendering (children render immediately)
 *  - Silently checks auth in the background
 *  - Provides optional user info (agent_id) for WebSocket connections
 *  - Works without authentication (mock mode is the default)
 */

export interface TeamUser {
  agent_id: string;
  display_name: string;
  avatar_url?: string;
}

interface TeamAuthState {
  /** The authenticated user, or null if not logged in */
  user: TeamUser | null;
  /** Whether the initial auth check is still in progress */
  isChecking: boolean;
  /** Whether a user is authenticated */
  isAuthenticated: boolean;
}

const TeamAuthContext = createContext<TeamAuthState>({
  user: null,
  isChecking: true,
  isAuthenticated: false,
});

const SKIP_AUTH = process.env.NEXT_PUBLIC_SKIP_AUTH === 'true';

const DEMO_USER: TeamUser = {
  agent_id: 'demo_user',
  display_name: '演示用户',
};

export function TeamAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TeamUser | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (SKIP_AUTH) {
      setUser(DEMO_USER);
      setIsChecking(false);
      return;
    }

    const checkAuth = async () => {
      try {
        const userData = await getCurrentUser();
        if (!cancelled && userData) {
          setUser({
            agent_id: userData.agent_id,
            display_name: userData.display_name,
            avatar_url: userData.avatar_url,
          });
        }
      } catch {
        // Auth check failed silently -- user is not logged in, which is fine
      } finally {
        if (!cancelled) {
          setIsChecking(false);
        }
      }
    };

    checkAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <TeamAuthContext.Provider
      value={{
        user,
        isChecking,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </TeamAuthContext.Provider>
  );
}

/**
 * Hook to access optional auth state within Team Matcher pages.
 * Always returns a value (never throws), so it's safe to use
 * even without TeamAuthProvider.
 */
export function useTeamAuth(): TeamAuthState {
  return useContext(TeamAuthContext);
}
