'use client';

import { useState, useRef, useCallback } from 'react';
import { getSceneConfig } from '@/lib/store-scenes';
import { assistDemandStream } from '@/lib/store-api';

interface DemandInputProps {
  sceneId: string | null;
  onSubmit: (intent: string, scope?: string) => void;
  isSubmitting: boolean;
  isAuthenticated?: boolean;
  onLoginRequest?: () => void;
  onAuthExpired?: () => void;
}

interface DemandExample {
  label: string;
  scope: string;
  text: string;
}

const DEMAND_EXAMPLES: DemandExample[] = [
  {
    label: '黑客松',
    scope: 'scene:hackathon',
    text: '我想做一个 AI 驱动的健康管理应用参加黑客松。我负责后端和机器学习（Python、PyTorch），需要找：\n\n1）一个前端/移动端开发，最好会 React Native\n2）一个有医疗健康领域知识的产品经理\n\n要求有黑客松经验，能 48 小时内快速出原型。',
  },
  {
    label: '跨场景',
    scope: 'all',
    text: '我在做一个教育科技创业项目，正在组建早期团队：\n\n1）技术合伙人 — 全栈开发经验，最好懂 AI\n2）了解 K12 教育市场的产品人\n3）有用户增长经验的运营\n\n愿意给早期期权，不限地点，远程协作。',
  },
  {
    label: '技能交换',
    scope: 'scene:skill_exchange',
    text: '我是 5 年经验的前端工程师，精通 React、TypeScript、Next.js。想学 Rust 和系统编程，转向底层开发方向。\n\n可以用前端开发辅导、代码审查和简历优化做交换。每周可安排 2-3 小时。',
  },
  {
    label: '招聘',
    scope: 'scene:recruitment',
    text: '招聘高级 AI 工程师：\n\n- 3 年以上机器学习工程经验\n- 熟悉 PyTorch，有大规模模型训练和部署经验\n- 加分：NLP 方向、分布式训练经验\n\n远程工作，薪资 40-60 万，期权另谈。',
  },
];

/**
 * 轻量级 Markdown 渲染：处理 **加粗**、段落、列表、换行。
 * 不引入外部依赖，够用就好。
 */
function renderMarkdown(text: string): React.ReactNode[] {
  const paragraphs = text.split(/\n{2,}/);
  const nodes: React.ReactNode[] = [];

  for (let i = 0; i < paragraphs.length; i++) {
    const para = paragraphs[i].trim();
    if (!para) continue;

    // 检查是否是列表段落（所有行以 - 或数字) 开头）
    const lines = para.split('\n');
    const isList = lines.every(
      (l) => /^\s*[-*]\s/.test(l) || /^\s*\d+[.)]\s/.test(l) || !l.trim(),
    );

    if (isList) {
      const items = lines.filter((l) => l.trim());
      nodes.push(
        <ul key={i} style={{ margin: '8px 0', paddingLeft: 20 }}>
          {items.map((item, j) => (
            <li key={j} style={{ marginBottom: 4 }}>
              {renderInline(item.replace(/^\s*[-*]\s*/, '').replace(/^\s*\d+[.)]\s*/, ''))}
            </li>
          ))}
        </ul>,
      );
    } else {
      // 普通段落，处理单个换行为 <br>
      const lineNodes: React.ReactNode[] = [];
      lines.forEach((line, j) => {
        if (j > 0) lineNodes.push(<br key={`br-${j}`} />);
        lineNodes.push(<span key={`l-${j}`}>{renderInline(line)}</span>);
      });
      nodes.push(
        <p key={i} style={{ margin: '8px 0' }}>
          {lineNodes}
        </p>,
      );
    }
  }

  return nodes;
}

/** 处理行内 **加粗** */
function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <strong key={match.index}>{match[1]}</strong>,
    );
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? parts : [text];
}

export function DemandInput({ sceneId, onSubmit, isSubmitting, isAuthenticated, onLoginRequest, onAuthExpired }: DemandInputProps) {
  const [text, setText] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [assistLoading, setAssistLoading] = useState<'polish' | 'surprise' | null>(null);
  const [assistError, setAssistError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scene = getSceneConfig(sceneId || 'hackathon');

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || isSubmitting) return;
    onSubmit(trimmed);
  };

  const handleChipClick = (chip: string) => {
    setText((prev) => {
      if (prev.includes(chip)) return prev;
      return prev ? `${prev}，${chip}` : chip;
    });
    setIsEditing(true);
  };

  const handleExampleClick = (example: DemandExample) => {
    setText(example.text);
    setIsEditing(false);
  };

  const handlePreviewClick = useCallback(() => {
    if (assistLoading) return;
    setIsEditing(true);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [assistLoading]);

  const handleAssist = async (mode: 'polish' | 'surprise') => {
    if (!isAuthenticated) {
      onLoginRequest?.();
      return;
    }
    if (mode === 'polish' && !text.trim()) return;
    setAssistLoading(mode);
    setAssistError(null);
    setIsEditing(false);
    try {
      const result = await assistDemandStream(
        {
          mode,
          scene_id: sceneId || '',
          raw_text: text.trim(),
        },
        (accumulated) => setText(accumulated),
      );
      setText(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('401') || msg.includes('登录')) {
        onAuthExpired?.();
        setAssistError('登录已过期，请重新登录');
      } else {
        setAssistError('分身暂时无法响应，请稍后再试');
      }
    } finally {
      setAssistLoading(null);
    }
  };

  // 显示 Markdown 预览：有内容 + 不在编辑模式（包括流式输出中）
  const showPreview = text.trim() && !isEditing;

  return (
    <div style={{ padding: '24px' }}>
      {assistLoading === 'surprise' && (
        <style>{`
          @keyframes surprise-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.04); }
          }
        `}</style>
      )}
      <div
        style={{
          position: 'relative',
          border: '1px solid rgba(0,0,0,0.1)',
          borderRadius: 12,
          backgroundColor: '#fff',
          overflow: 'hidden',
        }}
      >
        {showPreview ? (
          <div
            onClick={handlePreviewClick}
            style={{
              width: '100%',
              minHeight: 72,
              maxHeight: 400,
              overflowY: 'auto',
              padding: '12px 16px',
              fontSize: 15,
              lineHeight: 1.6,
              fontFamily: 'inherit',
              color: '#333',
              cursor: assistLoading ? 'default' : 'text',
            }}
          >
            {renderMarkdown(text)}
          </div>
        ) : (
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={() => setIsEditing(true)}
            onBlur={() => setIsEditing(false)}
            placeholder={scene.placeholder}
            rows={3}
            style={{
              width: '100%',
              padding: '16px',
              border: 'none',
              outline: 'none',
              resize: 'none',
              fontSize: 15,
              lineHeight: 1.6,
              fontFamily: 'inherit',
              backgroundColor: 'transparent',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                handleSubmit();
              }
            }}
          />
        )}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px 12px',
          }}
        >
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {scene.chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleChipClick(chip)}
                style={{
                  fontSize: 12,
                  padding: '4px 10px',
                  borderRadius: 12,
                  border: '1px solid rgba(0,0,0,0.08)',
                  backgroundColor: 'rgba(0,0,0,0.02)',
                  color: '#666',
                  cursor: 'pointer',
                }}
              >
                {chip}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {isAuthenticated && (
              <>
                <button
                  onClick={() => handleAssist('polish')}
                  disabled={!text.trim() || !!assistLoading}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 16,
                    border: '1.5px solid rgba(0,0,0,0.1)',
                    backgroundColor: 'transparent',
                    color: !text.trim() || assistLoading ? '#bbb' : '#666',
                    fontSize: 13,
                    cursor: !text.trim() || assistLoading ? 'default' : 'pointer',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {assistLoading === 'polish' ? '思考中...' : '让分身润色'}
                </button>
                <button
                  onClick={() => handleAssist('surprise')}
                  disabled={!!assistLoading}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 16,
                    border: '1.5px solid #F9A87C',
                    backgroundColor: assistLoading === 'surprise' ? 'rgba(249,168,124,0.08)' : 'transparent',
                    color: assistLoading === 'surprise' ? '#F9A87C' : assistLoading ? '#dbb' : '#F9A87C',
                    fontSize: 13,
                    cursor: assistLoading ? 'default' : 'pointer',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                    ...(assistLoading === 'surprise' ? { animation: 'surprise-pulse 1.5s ease-in-out infinite' } : {}),
                  }}
                >
                  {assistLoading === 'surprise' ? '捣乱中...' : '通向惊喜'}
                </button>
              </>
            )}
            <button
              onClick={handleSubmit}
              disabled={!text.trim() || isSubmitting}
              style={{
                padding: '8px 20px',
                borderRadius: 8,
                border: 'none',
                backgroundColor: text.trim() && !isSubmitting ? scene.primary : '#e0e0e0',
                color: text.trim() && !isSubmitting ? '#fff' : '#999',
                fontSize: 14,
                fontWeight: 600,
                cursor: text.trim() && !isSubmitting ? 'pointer' : 'default',
                transition: 'background-color 0.2s',
                whiteSpace: 'nowrap',
              }}
            >
              {isSubmitting ? '提交中...' : '发起协商'}
            </button>
          </div>
        </div>
      </div>

      {/* Assist error */}
      {assistError && (
        <div
          style={{
            padding: '8px 16px',
            marginTop: 8,
            fontSize: 13,
            color: '#c0392b',
            backgroundColor: 'rgba(192,57,43,0.06)',
            borderRadius: 8,
          }}
        >
          {assistError}
        </div>
      )}

      {/* Example demands */}
      <div
        style={{
          display: 'flex',
          gap: 6,
          marginTop: 8,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: 12, color: '#999' }}>示例：</span>
        {DEMAND_EXAMPLES.map((example) => (
          <button
            key={example.label}
            onClick={() => handleExampleClick(example)}
            style={{
              fontSize: 12,
              padding: '3px 10px',
              borderRadius: 10,
              border: '1px solid rgba(0,0,0,0.06)',
              backgroundColor: 'rgba(0,0,0,0.02)',
              color: '#888',
              cursor: 'pointer',
            }}
          >
            {example.label}
          </button>
        ))}
      </div>
    </div>
  );
}
