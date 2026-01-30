'use client';

import { useState, FormEvent, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import styles from './RequirementForm.module.css';

// Demo content for one-click experience
const DEMO_CONTENT = {
  title: '找一个技术合伙人',
  description: '我有一个创业想法，想做一个帮助自由职业者管理客户和项目的工具。我需要找一个技术合伙人，最好是全栈开发，愿意用业余时间一起做，可以给15%的股份。',
};

interface RequirementFormProps {
  onSubmit: (data: { title: string; description: string }) => Promise<void>;
  isSubmitting?: boolean;
  disabled?: boolean;
}

export function RequirementForm({
  onSubmit,
  isSubmitting = false,
  disabled = false,
}: RequirementFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isTyping, setIsTyping] = useState(false);
  const typingRef = useRef<{ cancelled: boolean }>({ cancelled: false });

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!title.trim()) newErrors.title = '请输入需求标题';
    if (title.length > 100) newErrors.title = '标题不能超过100字符';
    if (!description.trim()) newErrors.description = '请输入需求描述';
    if (description.length > 2000) newErrors.description = '描述不能超过2000字符';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate() || disabled || isSubmitting || isTyping) return;
    await onSubmit({ title, description });
  };

  // Typewriter effect function
  const typeText = useCallback(async (
    text: string,
    setter: (value: string | ((prev: string) => string)) => void,
    delay: number = 40
  ): Promise<void> => {
    for (let i = 0; i <= text.length; i++) {
      if (typingRef.current.cancelled) return;
      setter(text.slice(0, i));
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }, []);

  // Handle demo button click
  const handleDemoClick = useCallback(async () => {
    if (isTyping || isSubmitting || disabled) return;

    // Reset state
    typingRef.current.cancelled = false;
    setIsTyping(true);
    setErrors({});
    setTitle('');
    setDescription('');

    try {
      // Type title first (faster)
      await typeText(DEMO_CONTENT.title, setTitle, 35);

      if (typingRef.current.cancelled) return;

      // Small pause between title and description
      await new Promise(resolve => setTimeout(resolve, 200));

      if (typingRef.current.cancelled) return;

      // Type description (slightly slower for longer text)
      await typeText(DEMO_CONTENT.description, setDescription, 25);
    } finally {
      setIsTyping(false);
    }
  }, [isTyping, isSubmitting, disabled, typeText]);

  // Cancel typing if user starts editing
  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isTyping) {
      typingRef.current.cancelled = true;
      setIsTyping(false);
    }
    setTitle(e.target.value);
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (isTyping) {
      typingRef.current.cancelled = true;
      setIsTyping(false);
    }
    setDescription(e.target.value);
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {/* Demo Button */}
      <button
        type="button"
        className={styles.demoButton}
        onClick={handleDemoClick}
        disabled={isTyping || isSubmitting || disabled}
      >
        <span className={styles.demoIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        </span>
        <span>{isTyping ? '演示中...' : '一键体验'}</span>
      </button>

      <div className={styles.field}>
        <label className={styles.label}>需求标题</label>
        <input
          type="text"
          className={styles.input}
          value={title}
          onChange={handleTitleChange}
          placeholder="简要描述你的需求"
          disabled={disabled || isSubmitting}
          maxLength={100}
        />
        <div className={styles.fieldFooter}>
          {errors.title && <span className={styles.error}>{errors.title}</span>}
          <span className={styles.counter}>{title.length}/100</span>
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>需求描述</label>
        <textarea
          className={styles.textarea}
          value={description}
          onChange={handleDescriptionChange}
          placeholder="详细描述你的需求，包括背景、目标、期望结果等"
          disabled={disabled || isSubmitting}
          maxLength={2000}
          rows={6}
        />
        <div className={styles.fieldFooter}>
          {errors.description && <span className={styles.error}>{errors.description}</span>}
          <span className={styles.counter}>{description.length}/2000</span>
        </div>
      </div>

      <Button
        variant="primary"
        type="submit"
        disabled={disabled || isSubmitting || isTyping}
      >
        {isSubmitting ? '提交中...' : isTyping ? '请等待演示完成' : '提交需求'}
      </Button>
    </form>
  );
}