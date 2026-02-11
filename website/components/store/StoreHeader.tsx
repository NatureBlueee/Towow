'use client';

import { useStoreAuth, type StoreUser } from '@/hooks/useStoreAuth';

function getInitial(name: string): string {
  return name.charAt(0).toUpperCase();
}

function getAvatarColor(name: string): string {
  const colors = ['#F9A87C', '#D4B8D9', '#8FD5A3', '#FFE4B5', '#C4A0CA'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function UserAvatar({ user }: { user: StoreUser }) {
  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.display_name}
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          objectFit: 'cover',
        }}
      />
    );
  }

  return (
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: '50%',
        backgroundColor: getAvatarColor(user.display_name),
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 14,
        fontWeight: 600,
      }}
    >
      {getInitial(user.display_name)}
    </div>
  );
}

export function StoreHeader() {
  const { user, isAuthenticated, isLoading, login, logout } = useStoreAuth();

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 24px',
        borderBottom: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <span style={{ fontSize: 20, fontWeight: 600 }}>通爻网络</span>
        </a>
        <span
          style={{
            fontSize: 12,
            padding: '2px 8px',
            borderRadius: 4,
            backgroundColor: 'rgba(0,0,0,0.04)',
            color: '#666',
          }}
        >
          App Store
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isLoading ? (
          <span style={{ fontSize: 14, color: '#999' }}>...</span>
        ) : isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <UserAvatar user={user} />
            <span style={{ fontSize: 14, color: '#333' }}>
              {user.display_name}
            </span>
            <button
              onClick={logout}
              style={{
                fontSize: 12,
                color: '#999',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px 8px',
              }}
            >
              退出
            </button>
          </div>
        ) : (
          <button
            onClick={login}
            style={{
              fontSize: 14,
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid #D4B8D9',
              backgroundColor: '#fff',
              color: '#333',
              cursor: 'pointer',
            }}
          >
            连接你的 Agent
          </button>
        )}
      </div>
    </header>
  );
}
