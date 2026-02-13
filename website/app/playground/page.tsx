'use client';

import { useState, useEffect, useCallback } from 'react';
import { quickRegister, getScenes, type StoreScene } from '@/lib/store-api';
import { NegotiationProgress } from '@/components/store/NegotiationProgress';
import { PlanOutput } from '@/components/store/PlanOutput';
import { useStoreNegotiation } from '@/hooks/useStoreNegotiation';

type PlaygroundState = 'register' | 'ready';

const STORAGE_KEY = 'playground_agent_id';
const STORAGE_NAME_KEY = 'playground_display_name';

export default function PlaygroundPage() {
  const [pgState, setPgState] = useState<PlaygroundState>('register');
  const [agentId, setAgentId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [scenes, setScenes] = useState<StoreScene[]>([]);
  const negotiation = useStoreNegotiation();

  // Registration form
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [rawText, setRawText] = useState('');
  const [subscribe, setSubscribe] = useState(false);
  const [selectedScene, setSelectedScene] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState('');

  // Negotiation form
  const [intent, setIntent] = useState('');
  const [negScope, setNegScope] = useState('all');

  // Restore from localStorage
  useEffect(() => {
    const savedId = localStorage.getItem(STORAGE_KEY);
    const savedName = localStorage.getItem(STORAGE_NAME_KEY);
    if (savedId) {
      setAgentId(savedId);
      setDisplayName(savedName || '');
      setPgState('ready');
    }
  }, []);

  // Load scenes
  useEffect(() => {
    getScenes()
      .then((data) => setScenes(data.scenes))
      .catch(() => {});
  }, []);

  const handleRegister = useCallback(async () => {
    setRegError('');
    if (!email.trim()) {
      setRegError('请输入邮箱');
      return;
    }
    if (!name.trim()) {
      setRegError('请输入你的名字');
      return;
    }
    if (!rawText.trim()) {
      setRegError('请输入你的介绍');
      return;
    }

    setRegLoading(true);
    try {
      const result = await quickRegister({
        email: email.trim(),
        display_name: name.trim(),
        raw_text: rawText.trim(),
        subscribe,
        scene_id: selectedScene,
      });
      localStorage.setItem(STORAGE_KEY, result.agent_id);
      localStorage.setItem(STORAGE_NAME_KEY, result.display_name);
      setAgentId(result.agent_id);
      setDisplayName(result.display_name);
      setPgState('ready');
    } catch (err) {
      setRegError(err instanceof Error ? err.message : '注册失败');
    } finally {
      setRegLoading(false);
    }
  }, [email, name, rawText, subscribe, selectedScene]);

  const handleNegotiate = useCallback(() => {
    if (!intent.trim() || !agentId) return;
    negotiation.submit(intent.trim(), negScope, agentId);
  }, [intent, negScope, agentId, negotiation]);

  const handleReset = useCallback(() => {
    negotiation.reset();
    setIntent('');
  }, [negotiation]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_NAME_KEY);
    setAgentId(null);
    setDisplayName('');
    setPgState('register');
    negotiation.reset();
  }, [negotiation]);

  const showNegotiation = negotiation.phase !== 'idle';
  const showPlan =
    negotiation.planOutput ||
    negotiation.planJson ||
    negotiation.phase === 'completed';

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F8F6F3' }}>
      {/* Header */}
      <header
        style={{
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
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
        {pgState === 'ready' && (
          <button
            onClick={handleLogout}
            style={{
              fontSize: 13,
              color: '#999',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            重新注册
          </button>
        )}
      </header>

      {/* Content */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '48px 24px' }}>
        {pgState === 'register' ? (
          <RegisterForm
            email={email}
            setEmail={setEmail}
            name={name}
            setName={setName}
            rawText={rawText}
            setRawText={setRawText}
            subscribe={subscribe}
            setSubscribe={setSubscribe}
            selectedScene={selectedScene}
            setSelectedScene={setSelectedScene}
            scenes={scenes}
            loading={regLoading}
            error={regError}
            onSubmit={handleRegister}
          />
        ) : (
          <>
            {/* Agent Info */}
            <div style={{ marginBottom: 32, textAlign: 'center' }}>
              <p
                style={{
                  fontSize: 14,
                  color: '#999',
                  marginBottom: 4,
                }}
              >
                你的 Agent
              </p>
              <p
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  color: '#1A1A1A',
                }}
              >
                {displayName}
              </p>
            </div>

            {/* Negotiation Input */}
            {!showNegotiation && (
              <div>
                <h2
                  style={{
                    fontSize: 22,
                    fontWeight: 600,
                    color: '#1A1A1A',
                    marginBottom: 16,
                    textAlign: 'center',
                  }}
                >
                  描述你的需求
                </h2>

                {scenes.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <label
                      style={{
                        fontSize: 13,
                        color: '#666',
                        display: 'block',
                        marginBottom: 6,
                      }}
                    >
                      选择场景
                    </label>
                    <select
                      value={negScope}
                      onChange={(e) => setNegScope(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        fontSize: 14,
                        border: '1px solid #D4CFC8',
                        borderRadius: 8,
                        backgroundColor: '#fff',
                        color: '#333',
                      }}
                    >
                      <option value="all">全网络</option>
                      {scenes.map((s) => (
                        <option key={s.scene_id} value={`scene:${s.scene_id}`}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <textarea
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  placeholder="描述你想要做什么、需要什么样的协作伙伴..."
                  rows={4}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    fontSize: 14,
                    lineHeight: 1.6,
                    border: '1px solid #D4CFC8',
                    borderRadius: 8,
                    resize: 'vertical',
                    fontFamily: 'inherit',
                    boxSizing: 'border-box',
                  }}
                />

                <button
                  onClick={handleNegotiate}
                  disabled={!intent.trim()}
                  style={{
                    marginTop: 16,
                    width: '100%',
                    padding: '12px 0',
                    fontSize: 15,
                    fontWeight: 600,
                    color: '#fff',
                    backgroundColor: intent.trim() ? '#1A1A1A' : '#CCC',
                    border: 'none',
                    borderRadius: 8,
                    cursor: intent.trim() ? 'pointer' : 'not-allowed',
                    transition: 'background-color 0.2s',
                  }}
                >
                  发起协商
                </button>
              </div>
            )}

            {/* Negotiation Progress */}
            {showNegotiation && !showPlan && (
              <NegotiationProgress
                phase={negotiation.phase}
                participants={negotiation.participants}
                timeline={negotiation.timeline}
                error={negotiation.error}
                onReset={handleReset}
                totalAgentCount={negotiation.negotiation?.agent_count}
              />
            )}

            {/* Plan Output */}
            {showPlan && (
              <div>
                <PlanOutput
                  planText={negotiation.planOutput}
                  planJson={negotiation.planJson}
                  participants={negotiation.participants}
                />
                <div style={{ marginTop: 24, textAlign: 'center' }}>
                  <button
                    onClick={handleReset}
                    style={{
                      padding: '10px 32px',
                      fontSize: 14,
                      fontWeight: 500,
                      color: '#666',
                      backgroundColor: '#F0EDE8',
                      border: 'none',
                      borderRadius: 8,
                      cursor: 'pointer',
                    }}
                  >
                    发起新的协商
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ============ Register Form ============

interface RegisterFormProps {
  email: string;
  setEmail: (v: string) => void;
  name: string;
  setName: (v: string) => void;
  rawText: string;
  setRawText: (v: string) => void;
  subscribe: boolean;
  setSubscribe: (v: boolean) => void;
  selectedScene: string;
  setSelectedScene: (v: string) => void;
  scenes: StoreScene[];
  loading: boolean;
  error: string;
  onSubmit: () => void;
}

function RegisterForm({
  email,
  setEmail,
  name,
  setName,
  rawText,
  setRawText,
  subscribe,
  setSubscribe,
  selectedScene,
  setSelectedScene,
  scenes,
  loading,
  error,
  onSubmit,
}: RegisterFormProps) {
  const inputStyle = {
    width: '100%',
    padding: '10px 14px',
    fontSize: 14,
    border: '1px solid #D4CFC8',
    borderRadius: 8,
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  };

  const labelStyle = {
    fontSize: 13,
    fontWeight: 500 as const,
    color: '#555',
    display: 'block',
    marginBottom: 6,
  };

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 36 }}>
        <h1
          style={{
            fontSize: 26,
            fontWeight: 700,
            color: '#1A1A1A',
            marginBottom: 8,
          }}
        >
          加入通爻网络
        </h1>
        <p style={{ fontSize: 15, color: '#666', lineHeight: 1.6 }}>
          粘贴你的简历、自我介绍、或者任何能代表你的文字。
          <br />
          网络会把你变成一个 Agent，参与未来的协商。
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Email */}
        <div>
          <label style={labelStyle}>邮箱</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            style={inputStyle}
          />
        </div>

        {/* Display Name */}
        <div>
          <label style={labelStyle}>名字</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="你想在网络中显示的名字"
            style={inputStyle}
          />
        </div>

        {/* Raw Text */}
        <div>
          <label style={labelStyle}>关于你</label>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="粘贴你的简历、自我介绍、LinkedIn 摘要、或者随便写点什么。越具体越好——这些文字会决定你在网络中跟谁产生共振。"
            rows={10}
            style={{
              ...inputStyle,
              lineHeight: 1.6,
              resize: 'vertical',
            }}
          />
        </div>

        {/* Scene */}
        {scenes.length > 0 && (
          <div>
            <label style={labelStyle}>想加入的场景（可选）</label>
            <select
              value={selectedScene}
              onChange={(e) => setSelectedScene(e.target.value)}
              style={inputStyle}
            >
              <option value="">全部场景</option>
              {scenes.map((s) => (
                <option key={s.scene_id} value={s.scene_id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Subscribe */}
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 14,
            color: '#555',
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={subscribe}
            onChange={(e) => setSubscribe(e.target.checked)}
            style={{ width: 16, height: 16 }}
          />
          有人对我发出共振时通知我
        </label>

        {/* Error */}
        {error && (
          <p style={{ fontSize: 14, color: '#D44', margin: 0 }}>{error}</p>
        )}

        {/* Submit */}
        <button
          onClick={onSubmit}
          disabled={loading}
          style={{
            padding: '14px 0',
            fontSize: 15,
            fontWeight: 600,
            color: '#fff',
            backgroundColor: loading ? '#999' : '#1A1A1A',
            border: 'none',
            borderRadius: 8,
            cursor: loading ? 'wait' : 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          {loading ? '加入中...' : '加入网络'}
        </button>
      </div>
    </div>
  );
}
