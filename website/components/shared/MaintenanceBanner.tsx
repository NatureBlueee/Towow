'use client';

/**
 * Maintenance banner displayed when backend services are unavailable.
 * Shows a notice and redirects users to static content.
 *
 * This component is temporary and should be removed once the backend is restored.
 */
export function MaintenanceBanner({ pageName }: { pageName?: string }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#F8F6F3',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <header
        style={{
          padding: '16px 24px',
          borderBottom: '1px solid #E8E4DF',
        }}
      >
        <a
          href="/"
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: '#1A1A1A',
            textDecoration: 'none',
          }}
        >
          通爻
        </a>
      </header>

      {/* Content */}
      <main
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px 24px',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: 480 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: '50%',
              backgroundColor: '#F0EDE8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              fontSize: 28,
            }}
          >
            <span role="img" aria-label="maintenance">&#128295;</span>
          </div>

          <h1
            style={{
              fontSize: 24,
              fontWeight: 700,
              color: '#1A1A1A',
              marginBottom: 12,
            }}
          >
            {pageName ? `${pageName} - ` : ''}系统维护中
          </h1>

          <p
            style={{
              fontSize: 15,
              color: '#666',
              lineHeight: 1.6,
              marginBottom: 32,
            }}
          >
            服务器正在维护升级，该功能暂时不可用。
            <br />
            我们正在全力修复，请稍后再来。
          </p>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a
              href="/"
              style={{
                padding: '10px 24px',
                fontSize: 14,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: '#1A1A1A',
                borderRadius: 8,
                textDecoration: 'none',
                transition: 'background-color 0.2s',
              }}
            >
              返回首页
            </a>
            <a
              href="/articles"
              style={{
                padding: '10px 24px',
                fontSize: 14,
                fontWeight: 600,
                color: '#555',
                backgroundColor: '#F0EDE8',
                borderRadius: 8,
                textDecoration: 'none',
                transition: 'background-color 0.2s',
              }}
            >
              浏览文章
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
