'use client';

import { useState, useEffect, useCallback } from 'react';
import styles from './SecondMeLogin.module.css';

interface UserInfo {
  agent_id: string;
  display_name: string;
  avatar_url?: string;
}

export function SecondMeLogin() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = useCallback(() => {
    const returnTo = encodeURIComponent(window.location.pathname);
    window.location.href = `/api/auth/secondme/start?return_to=${returnTo}`;
  }, []);

  const handleLogout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    setUser(null);
  }, []);

  if (loading) return null;

  if (user) {
    return (
      <div className={styles.userBar}>
        {user.avatar_url && (
          <img src={user.avatar_url} alt="" className={styles.avatar} />
        )}
        <span className={styles.userName}>{user.display_name}</span>
        <button onClick={handleLogout} className={styles.logoutBtn}>
          退出
        </button>
      </div>
    );
  }

  return (
    <button onClick={handleLogin} className={styles.loginBtn}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
        <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
      用 SecondMe 登录
    </button>
  );
}
