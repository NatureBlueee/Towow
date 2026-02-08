'use client';

import { useState } from 'react';
import styles from './DemandInput.module.css';

interface DemandInputProps {
  onSubmit: (intent: string) => void;
  disabled?: boolean;
}

export function DemandInput({ onSubmit, disabled }: DemandInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={styles.container}>
      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe what you need..."
        rows={4}
        disabled={disabled}
      />
      <button
        className={styles.submitButton}
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
      >
        Submit
      </button>
    </div>
  );
}
