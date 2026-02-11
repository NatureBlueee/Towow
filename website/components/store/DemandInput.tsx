'use client';

import { useState } from 'react';
import { getSceneConfig } from '@/lib/store-scenes';

interface DemandInputProps {
  sceneId: string | null;
  onSubmit: (intent: string, scope?: string) => void;
  isSubmitting: boolean;
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

export function DemandInput({ sceneId, onSubmit, isSubmitting }: DemandInputProps) {
  const [text, setText] = useState('');
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
  };

  const handleExampleClick = (example: DemandExample) => {
    setText(example.text);
  };

  return (
    <div style={{ padding: '24px' }}>
      <div
        style={{
          position: 'relative',
          border: '1px solid rgba(0,0,0,0.1)',
          borderRadius: 12,
          backgroundColor: '#fff',
          overflow: 'hidden',
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
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
            }}
          >
            {isSubmitting ? '提交中...' : '发起协商'}
          </button>
        </div>
      </div>

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
