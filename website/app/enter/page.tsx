'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { quickRegister } from '@/lib/store-api';

type FormTab = 'email' | 'phone';

const LOCAL_AGENT_KEY = 'playground_agent_id';
const LOCAL_NAME_KEY = 'playground_display_name';

export default function EnterPage() {
  const router = useRouter();
  const [formTab, setFormTab] = useState<FormTab>('email');
  const [toast, setToast] = useState<string | null>(null);
  const [existingName, setExistingName] = useState<string | null>(null);

  // Form fields
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [rawText, setRawText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Detect existing local registration
  useEffect(() => {
    const agentId = localStorage.getItem(LOCAL_AGENT_KEY);
    const displayName = localStorage.getItem(LOCAL_NAME_KEY);
    if (agentId && displayName) {
      setExistingName(displayName);
    }
  }, []);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleSecondMe = () => {
    window.location.href = '/api/auth/secondme/start?return_to=/store/';
  };

  const handleGoogle = () => {
    showToast('Google 登录即将开放，请先使用其他方式');
  };

  const handleRegister = useCallback(async () => {
    setError('');
    if (formTab === 'email' && !email.trim()) {
      setError('请输入邮箱');
      return;
    }
    if (formTab === 'phone' && !phone.trim()) {
      setError('请输入手机号');
      return;
    }
    if (!name.trim()) {
      setError('请输入你的名字');
      return;
    }
    if (!rawText.trim()) {
      setError('请简单介绍自己');
      return;
    }

    setLoading(true);
    try {
      const result = await quickRegister({
        email: formTab === 'email' ? email.trim() : '',
        phone: formTab === 'phone' ? phone.trim() : '',
        display_name: name.trim(),
        raw_text: rawText.trim(),
      });
      localStorage.setItem(LOCAL_AGENT_KEY, result.agent_id);
      localStorage.setItem(LOCAL_NAME_KEY, result.display_name);
      router.push('/store');
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [formTab, email, phone, name, rawText, router]);

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#F8F6F3',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Scoped styles for focus and hover states */}
      <style>{`
        .enter-input:focus {
          outline: none;
          border-color: #D4B8D9;
          box-shadow: 0 0 0 3px rgba(212,184,217,0.15);
        }
        .enter-oauth-btn:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.06);
          transform: translateY(-1px);
        }
        .enter-oauth-btn:active {
          transform: translateY(0);
        }
        .enter-submit-btn:hover:not(:disabled) {
          background-color: #333 !important;
        }
        .enter-mcp-link:hover {
          border-color: #D4B8D9 !important;
        }
        @media (prefers-reduced-motion: reduce) {
          .enter-oauth-btn, .enter-submit-btn, .enter-mcp-link {
            transition: none !important;
          }
        }
      `}</style>

      {/* Toast */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: 'fixed',
            top: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '10px 24px',
            backgroundColor: '#1A1A1A',
            color: '#fff',
            fontSize: 14,
            borderRadius: 8,
            zIndex: 1000,
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          }}
        >
          {toast}
        </div>
      )}

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

      {/* Main content */}
      <main
        style={{
          flex: 1,
          display: 'flex',
          justifyContent: 'center',
          padding: '48px 24px 64px',
        }}
      >
        <div style={{ width: '100%', maxWidth: 440 }}>
          {/* Title */}
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h1
              style={{
                fontSize: 26,
                fontWeight: 700,
                color: '#1A1A1A',
                marginBottom: 8,
              }}
            >
              选择你的进入方式
            </h1>
            <p style={{ fontSize: 15, color: '#666', lineHeight: 1.5 }}>
              不同方式，不同起点
            </p>
          </div>

          {/* Existing registration notice */}
          {existingName && (
            <div
              style={{
                padding: '14px 16px',
                marginBottom: 24,
                backgroundColor: '#fff',
                border: '1px solid #D4B8D9',
                borderRadius: 10,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: 14, color: '#555' }}>
                你已经以 <strong style={{ color: '#1A1A1A' }}>{existingName}</strong> 的身份加入网络
              </span>
              <button
                onClick={() => router.push('/store')}
                style={{
                  padding: '6px 16px',
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#fff',
                  backgroundColor: '#1A1A1A',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                继续
              </button>
            </div>
          )}

          {/* OAuth buttons */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
            <button
              className="enter-oauth-btn"
              onClick={handleSecondMe}
              aria-label="通过 SecondMe 登录"
              style={{
                flex: 1,
                padding: '16px',
                borderRadius: 10,
                border: '1.5px solid #D4B8D9',
                backgroundColor: '#fff',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 600, color: '#1A1A1A', marginBottom: 4 }}>
                SecondMe
              </div>
              <div style={{ fontSize: 12, color: '#888' }}>
                AI 分身，完整体验
              </div>
            </button>
            <button
              className="enter-oauth-btn"
              onClick={handleGoogle}
              aria-label="Google 登录（即将开放）"
              style={{
                flex: 1,
                padding: '16px',
                borderRadius: 10,
                border: '1.5px solid #E8E4DF',
                backgroundColor: '#FAFAF8',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s ease',
                opacity: 0.6,
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 600, color: '#999', marginBottom: 4 }}>
                Google
              </div>
              <div style={{ fontSize: 12, color: '#BBB' }}>
                即将开放
              </div>
            </button>
          </div>

          {/* Divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              marginBottom: 28,
            }}
          >
            <div style={{ flex: 1, height: 1, backgroundColor: '#E8E4DF' }} />
            <span style={{ fontSize: 13, color: '#AAA', whiteSpace: 'nowrap' }}>
              或者直接加入
            </span>
            <div style={{ flex: 1, height: 1, backgroundColor: '#E8E4DF' }} />
          </div>

          {/* Tab switcher */}
          <div
            role="tablist"
            aria-label="注册方式"
            style={{
              display: 'flex',
              marginBottom: 20,
              backgroundColor: '#F0EDE8',
              borderRadius: 8,
              padding: 3,
            }}
          >
            {(['email', 'phone'] as FormTab[]).map((tab) => (
              <button
                key={tab}
                role="tab"
                aria-selected={formTab === tab}
                onClick={() => { setFormTab(tab); setError(''); }}
                style={{
                  flex: 1,
                  padding: '10px 0',
                  fontSize: 13,
                  fontWeight: 500,
                  color: formTab === tab ? '#1A1A1A' : '#888',
                  backgroundColor: formTab === tab ? '#fff' : 'transparent',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: formTab === tab ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                }}
              >
                {tab === 'email' ? '邮箱' : '手机号'}
              </button>
            ))}
          </div>

          {/* Registration form */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleRegister(); }}
            style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
          >
            {/* Email or Phone */}
            {formTab === 'email' ? (
              <div>
                <label htmlFor="enter-email" style={labelStyle}>邮箱</label>
                <input
                  id="enter-email"
                  className="enter-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  autoComplete="email"
                  style={inputStyle}
                />
              </div>
            ) : (
              <div>
                <label htmlFor="enter-phone" style={labelStyle}>手机号</label>
                <input
                  id="enter-phone"
                  className="enter-input"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="13800138000"
                  autoComplete="tel"
                  style={inputStyle}
                />
              </div>
            )}

            {/* Name */}
            <div>
              <label htmlFor="enter-name" style={labelStyle}>名字</label>
              <input
                id="enter-name"
                className="enter-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="你想在网络中显示的名字"
                autoComplete="name"
                style={inputStyle}
              />
            </div>

            {/* Raw text */}
            <div>
              <label htmlFor="enter-about" style={labelStyle}>关于你</label>
              <textarea
                id="enter-about"
                className="enter-input"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="简历、技能、兴趣——任何能代表你的文字。越具体，共振越精准。"
                rows={4}
                style={{
                  ...inputStyle,
                  lineHeight: 1.6,
                  resize: 'vertical',
                }}
              />
            </div>

            {/* Error */}
            {error && (
              <p role="alert" style={{ fontSize: 13, color: '#C0392B', margin: 0 }}>
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              className="enter-submit-btn"
              type="submit"
              disabled={loading}
              style={{
                padding: '13px 0',
                fontSize: 15,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: loading ? '#999' : '#1A1A1A',
                border: 'none',
                borderRadius: 8,
                cursor: loading ? 'wait' : 'pointer',
                transition: 'background-color 0.2s ease',
              }}
            >
              {loading ? '加入中...' : '加入网络'}
            </button>
          </form>

          {/* Developer divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              margin: '36px 0 20px',
            }}
          >
            <div style={{ flex: 1, height: 1, backgroundColor: '#E8E4DF' }} />
            <span style={{ fontSize: 13, color: '#AAA', whiteSpace: 'nowrap' }}>
              开发者？
            </span>
            <div style={{ flex: 1, height: 1, backgroundColor: '#E8E4DF' }} />
          </div>

          {/* MCP button */}
          <a
            className="enter-mcp-link"
            href="https://modelcontextprotocol.io"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'block',
              padding: '16px',
              borderRadius: 10,
              border: '1.5px solid #E8E4DF',
              backgroundColor: '#fff',
              textDecoration: 'none',
              cursor: 'pointer',
              transition: 'border-color 0.2s ease',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1A1A1A', marginBottom: 4 }}>
              MCP · 在你的 IDE 中连接通爻网络
            </div>
            <div style={{ fontSize: 12, color: '#888' }}>
              通过 Model Context Protocol 接入，无需离开编辑器
            </div>
          </a>
        </div>
      </main>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 13,
  fontWeight: 500,
  color: '#555',
  marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '11px 14px',
  fontSize: 14,
  border: '1px solid #D4CFC8',
  borderRadius: 8,
  fontFamily: 'inherit',
  boxSizing: 'border-box',
  backgroundColor: '#fff',
  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
};
