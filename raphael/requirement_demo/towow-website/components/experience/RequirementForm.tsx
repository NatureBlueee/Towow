'use client';

import { useState, FormEvent } from 'react';
import { Button } from '@/components/ui/Button';
import styles from './RequirementForm.module.css';

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
    if (!validate() || disabled || isSubmitting) return;
    await onSubmit({ title, description });
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <label className={styles.label}>需求标题</label>
        <input
          type="text"
          className={styles.input}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
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
          onChange={(e) => setDescription(e.target.value)}
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
        disabled={disabled || isSubmitting}
      >
        {isSubmitting ? '提交中...' : '提交需求'}
      </Button>
    </form>
  );
}