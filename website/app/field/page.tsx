'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getFieldStats,
  depositIntent,
  matchIntents,
  matchOwners,
  loadProfiles,
  type FieldStats,
  type MatchResponse,
  type OwnerMatchResponse,
} from '@/lib/field-api';

type Tab = 'match' | 'match-owners' | 'deposit';

export default function FieldPage() {
  const [tab, setTab] = useState<Tab>('match');
  const [stats, setStats] = useState<FieldStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingProfiles, setLoadingProfiles] = useState(false);

  // Match state
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(10);
  const [matchResults, setMatchResults] = useState<MatchResponse | null>(null);
  const [ownerResults, setOwnerResults] = useState<OwnerMatchResponse | null>(null);
  const [expandedOwners, setExpandedOwners] = useState<Set<string>>(new Set());
  const [expandedIntents, setExpandedIntents] = useState<Set<string>>(new Set());

  // Deposit state
  const [depositText, setDepositText] = useState('');
  const [depositOwner, setDepositOwner] = useState('');
  const [depositMsg, setDepositMsg] = useState('');

  // Error
  const [error, setError] = useState('');

  const refreshStats = useCallback(async () => {
    try {
      const s = await getFieldStats();
      setStats(s);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  const handleLoadProfiles = useCallback(async () => {
    setLoadingProfiles(true);
    setError('');
    try {
      const res = await loadProfiles();
      setStats({ intent_count: res.total_intents, owner_count: res.total_owners });
      if (res.loaded === 0) {
        setError(res.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profiles');
    } finally {
      setLoadingProfiles(false);
    }
  }, []);

  const handleMatch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setMatchResults(null);
    setOwnerResults(null);
    try {
      if (tab === 'match') {
        const res = await matchIntents(query.trim(), topK);
        setMatchResults(res);
      } else {
        const res = await matchOwners(query.trim(), topK);
        setOwnerResults(res);
        setExpandedOwners(new Set());
      }
      setExpandedIntents(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Match failed');
    } finally {
      setLoading(false);
    }
  }, [query, tab, topK]);

  const handleDeposit = useCallback(async () => {
    if (!depositText.trim() || !depositOwner.trim()) return;
    setLoading(true);
    setError('');
    setDepositMsg('');
    try {
      const res = await depositIntent(depositText.trim(), depositOwner.trim());
      setDepositMsg(res.message);
      setDepositText('');
      refreshStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Deposit failed');
    } finally {
      setLoading(false);
    }
  }, [depositText, depositOwner, refreshStats]);

  const toggleOwner = (owner: string) => {
    setExpandedOwners(prev => {
      const next = new Set(prev);
      if (next.has(owner)) next.delete(owner);
      else next.add(owner);
      return next;
    });
  };

  const toggleIntent = (id: string) => {
    setExpandedIntents(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--c-bg, #F8F6F3)' }}>
      {/* Header */}
      <header style={{
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #E8E4DF',
      }}>
        <a href="/" style={{
          fontSize: 18, fontWeight: 700,
          color: 'var(--c-text-main, #1A1A1A)',
          textDecoration: 'none',
        }}>
          通爻
        </a>
        <span style={{ fontSize: 13, color: '#999' }}>Intent Field Explorer</span>
      </header>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '32px 24px' }}>
        {/* Stats Bar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px',
          backgroundColor: '#fff',
          borderRadius: 12,
          border: '1px solid #E8E4DF',
          marginBottom: 24,
        }}>
          <div style={{ display: 'flex', gap: 32 }}>
            <StatBadge label="Intents" value={stats?.intent_count ?? '—'} />
            <StatBadge label="Owners" value={stats?.owner_count ?? '—'} />
          </div>
          <button
            onClick={handleLoadProfiles}
            disabled={loadingProfiles}
            style={{
              padding: '8px 16px',
              fontSize: 13, fontWeight: 500,
              color: '#fff',
              backgroundColor: loadingProfiles ? '#999' : '#1A1A1A',
              border: 'none', borderRadius: 8,
              cursor: loadingProfiles ? 'wait' : 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            {loadingProfiles ? 'Loading...' : 'Load Sample Data'}
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex', gap: 4,
          backgroundColor: '#F0EDE8', borderRadius: 10,
          padding: 4, marginBottom: 24,
        }}>
          {([
            ['match', 'Match'],
            ['match-owners', 'Match Owners'],
            ['deposit', 'Deposit'],
          ] as [Tab, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setTab(key); setError(''); }}
              style={{
                flex: 1,
                padding: '10px 0',
                fontSize: 14, fontWeight: tab === key ? 600 : 400,
                color: tab === key ? '#1A1A1A' : '#888',
                backgroundColor: tab === key ? '#fff' : 'transparent',
                border: 'none', borderRadius: 8,
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: tab === key ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '10px 14px', marginBottom: 16,
            fontSize: 13, color: '#B44',
            backgroundColor: '#FFF5F5', borderRadius: 8,
            border: '1px solid #FECACA',
          }}>
            {error}
          </div>
        )}

        {/* Match / Match Owners */}
        {(tab === 'match' || tab === 'match-owners') && (
          <div>
            <div style={{ position: 'relative', marginBottom: 20 }}>
              <textarea
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleMatch(); }}
                placeholder="输入查询... (Cmd+Enter 搜索)"
                rows={3}
                style={{
                  width: '100%', padding: '14px 16px',
                  fontSize: 15, lineHeight: 1.6,
                  border: '1px solid #D4CFC8', borderRadius: 10,
                  resize: 'vertical', fontFamily: 'inherit',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s',
                }}
              />
              <div style={{
                position: 'absolute', right: 10, bottom: 10,
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#999' }}>
                  K
                  <input
                    type="number"
                    value={topK}
                    onChange={e => setTopK(Math.max(1, Math.min(100, parseInt(e.target.value) || 10)))}
                    min={1}
                    max={100}
                    style={{
                      width: 44, padding: '4px 6px', fontSize: 12,
                      border: '1px solid #D4CFC8', borderRadius: 6,
                      textAlign: 'center', fontFamily: 'inherit',
                    }}
                  />
                </label>
                <button
                  onClick={handleMatch}
                  disabled={loading || !query.trim()}
                  style={{
                    padding: '8px 20px',
                    fontSize: 13, fontWeight: 600,
                    color: '#fff',
                    backgroundColor: loading || !query.trim() ? '#CCC' : '#1A1A1A',
                    border: 'none', borderRadius: 8,
                    cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
                  }}
                >
                  {loading ? '...' : 'Search'}
                </button>
              </div>
            </div>

            {/* Intent Match Results */}
            {tab === 'match' && matchResults && (
              <ResultsContainer
                queryTime={matchResults.query_time_ms}
                total={matchResults.total_intents}
                count={matchResults.results.length}
              >
                {matchResults.results.map((r, i) => (
                  <IntentCard
                    key={r.intent_id}
                    rank={i + 1}
                    result={r}
                    expanded={expandedIntents.has(r.intent_id)}
                    onToggle={() => toggleIntent(r.intent_id)}
                  />
                ))}
                {matchResults.results.length === 0 && (
                  <EmptyResults />
                )}
              </ResultsContainer>
            )}

            {/* Owner Match Results */}
            {tab === 'match-owners' && ownerResults && (
              <ResultsContainer
                queryTime={ownerResults.query_time_ms}
                total={ownerResults.total_intents}
                count={ownerResults.results.length}
                label={`${ownerResults.total_owners} owners`}
              >
                {ownerResults.results.map((r, i) => (
                  <OwnerCard
                    key={r.owner}
                    rank={i + 1}
                    result={r}
                    expanded={expandedOwners.has(r.owner)}
                    onToggle={() => toggleOwner(r.owner)}
                  />
                ))}
                {ownerResults.results.length === 0 && (
                  <EmptyResults />
                )}
              </ResultsContainer>
            )}
          </div>
        )}

        {/* Deposit */}
        {tab === 'deposit' && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Owner</label>
              <input
                type="text"
                value={depositOwner}
                onChange={e => setDepositOwner(e.target.value)}
                placeholder="e.g. alice, agent_42"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Text</label>
              <textarea
                value={depositText}
                onChange={e => setDepositText(e.target.value)}
                placeholder="Intent text to deposit into the field..."
                rows={5}
                style={{ ...inputStyle, lineHeight: 1.6, resize: 'vertical' }}
              />
            </div>
            <button
              onClick={handleDeposit}
              disabled={loading || !depositText.trim() || !depositOwner.trim()}
              style={{
                width: '100%', padding: '12px 0',
                fontSize: 15, fontWeight: 600,
                color: '#fff',
                backgroundColor: loading || !depositText.trim() || !depositOwner.trim() ? '#CCC' : '#1A1A1A',
                border: 'none', borderRadius: 8,
                cursor: loading ? 'wait' : 'pointer',
                transition: 'background-color 0.2s',
              }}
            >
              {loading ? 'Depositing...' : 'Deposit'}
            </button>
            {depositMsg && (
              <div style={{
                marginTop: 12, padding: '10px 14px',
                fontSize: 13, color: '#2A7A3A',
                backgroundColor: '#F0FFF4', borderRadius: 8,
                border: '1px solid #C6F6D5',
              }}>
                {depositMsg}
              </div>
            )}
          </div>
        )}

        {/* Example Queries */}
        {(tab === 'match' || tab === 'match-owners') && !matchResults && !ownerResults && (
          <div style={{ marginTop: 8 }}>
            <p style={{ fontSize: 12, color: '#999', marginBottom: 10 }}>Try:</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {[
                'Rust 后端开发',
                '需要一个设计师做品牌',
                'AI 产品经理',
                '用技术做点有意义的事',
                'someone who can teach me ML',
              ].map(q => (
                <button
                  key={q}
                  onClick={() => setQuery(q)}
                  style={{
                    padding: '6px 12px', fontSize: 12,
                    color: '#666', backgroundColor: '#F5F3F0',
                    border: '1px solid #E8E4DF', borderRadius: 16,
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============ Shared Styles ============

const labelStyle: React.CSSProperties = {
  fontSize: 13, fontWeight: 500,
  color: '#555', display: 'block', marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 14px',
  fontSize: 14,
  border: '1px solid #D4CFC8', borderRadius: 8,
  fontFamily: 'inherit', boxSizing: 'border-box',
};

// ============ Sub-components ============

function StatBadge({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1A1A1A' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function ResultsContainer({
  queryTime, total, count, label, children,
}: {
  queryTime: number;
  total: number;
  count: number;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: 12, color: '#999', marginBottom: 12,
      }}>
        <span>{count} results from {label || `${total} intents`}</span>
        <span>{queryTime.toFixed(1)} ms</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {children}
      </div>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const hue = Math.round(score * 120); // 0=red, 60=yellow, 120=green
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      minWidth: 90,
    }}>
      <div style={{
        width: 50, height: 6, borderRadius: 3,
        backgroundColor: '#E8E4DF', overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: 3,
          backgroundColor: `hsl(${hue}, 60%, 50%)`,
          transition: 'width 0.3s',
        }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color: '#555', fontVariantNumeric: 'tabular-nums' }}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

function IntentCard({ rank, result, expanded, onToggle }: {
  rank: number;
  result: { intent_id: string; score: number; owner: string; text: string; metadata: Record<string, unknown> };
  expanded: boolean;
  onToggle: () => void;
}) {
  const isLong = result.text.length > 150;
  const displayText = expanded || !isLong ? result.text : result.text.slice(0, 150) + '...';
  const hasMetadata = Object.keys(result.metadata).length > 0;

  return (
    <div style={{
      backgroundColor: '#fff', borderRadius: 10,
      border: '1px solid #E8E4DF',
      overflow: 'hidden',
    }}>
      <div
        onClick={onToggle}
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          transition: 'background-color 0.15s',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 22, height: 22, borderRadius: '50%',
              backgroundColor: '#F0EDE8',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 600, color: '#888',
            }}>
              {rank}
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A' }}>
              {result.owner}
            </span>
          </div>
          <ScoreBar score={result.score} />
        </div>
        <p style={{
          fontSize: 13, color: '#555', lineHeight: 1.6, margin: 0,
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {displayText}
        </p>
        {isLong && !expanded && (
          <span style={{ fontSize: 12, color: '#999', cursor: 'pointer' }}>show more</span>
        )}
      </div>
      {expanded && (
        <div style={{
          borderTop: '1px solid #F0EDE8',
          padding: '8px 16px 10px',
          fontSize: 11, color: '#999',
          display: 'flex', flexDirection: 'column', gap: 4,
        }}>
          <span>intent_id: {result.intent_id}</span>
          {hasMetadata && (
            <span>metadata: {JSON.stringify(result.metadata)}</span>
          )}
        </div>
      )}
    </div>
  );
}

function OwnerCard({ rank, result, expanded, onToggle }: {
  rank: number;
  result: { owner: string; score: number; top_intents: Array<{ intent_id: string; score: number; owner: string; text: string }> };
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={{
      backgroundColor: '#fff', borderRadius: 10,
      border: '1px solid #E8E4DF',
      overflow: 'hidden',
    }}>
      <div
        onClick={onToggle}
        style={{
          padding: '12px 16px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          cursor: 'pointer',
          transition: 'background-color 0.15s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 22, height: 22, borderRadius: '50%',
            backgroundColor: '#F0EDE8',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 600, color: '#888',
          }}>
            {rank}
          </span>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#1A1A1A' }}>
            {result.owner}
          </span>
          <span style={{ fontSize: 12, color: '#999' }}>
            ({result.top_intents.length} intent{result.top_intents.length > 1 ? 's' : ''})
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ScoreBar score={result.score} />
          <span style={{ fontSize: 14, color: '#999', transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}>
            &#9654;
          </span>
        </div>
      </div>
      {expanded && (
        <div style={{
          borderTop: '1px solid #F0EDE8',
          padding: '8px 16px 12px',
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {result.top_intents.map(intent => (
            <div key={intent.intent_id} style={{
              padding: '8px 12px',
              backgroundColor: '#FAFAF8', borderRadius: 8,
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12,
              }}>
                <p style={{
                  fontSize: 12, color: '#555', lineHeight: 1.6, margin: 0, flex: 1,
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}>
                  {intent.text}
                </p>
                <ScoreBar score={intent.score} />
              </div>
              <div style={{ fontSize: 10, color: '#BBB', marginTop: 4 }}>
                {intent.intent_id}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyResults() {
  return (
    <div style={{
      textAlign: 'center', padding: '32px 0',
      color: '#999', fontSize: 14,
    }}>
      No results found. Try loading sample data first.
    </div>
  );
}
