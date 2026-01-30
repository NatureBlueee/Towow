'use client';

import { useState, useCallback } from 'react';
import { EXAMPLE_REQUIREMENTS } from '../shared/types';
import styles from './Stage1.module.css';

interface RequirementInputProps {
  onSubmit: (requirement: string) => void;
  isSubmitting?: boolean;
}

export function RequirementInput({
  onSubmit,
  isSubmitting = false,
}: RequirementInputProps) {
  const [requirement, setRequirement] = useState('');

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (requirement.trim() && !isSubmitting) {
        onSubmit(requirement.trim());
      }
    },
    [requirement, isSubmitting, onSubmit]
  );

  const handleExampleClick = useCallback((text: string) => {
    setRequirement(text);
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>ToWow Experience</h1>
        <p className={styles.subtitle}>
          描述你的需求，AI Agent 们将协商出最佳方案
        </p>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.inputWrapper}>
          <textarea
            className={styles.textarea}
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            placeholder="描述你的需求..."
            rows={4}
            disabled={isSubmitting}
            aria-label="需求描述"
          />
          <button
            type="submit"
            className={styles.submitButton}
            disabled={!requirement.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <span className={styles.spinner} />
            ) : (
              <>
                <span>提交</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </>
            )}
          </button>
        </div>
      </form>

      <div className={styles.examples}>
        <p className={styles.examplesLabel}>试试这些示例：</p>
        <div className={styles.exampleList}>
          {EXAMPLE_REQUIREMENTS.map((example) => (
            <button
              key={example.id}
              className={styles.exampleButton}
              onClick={() => handleExampleClick(example.text)}
              disabled={isSubmitting}
            >
              <span className={styles.exampleCategory}>{example.category}</span>
              <span className={styles.exampleText}>{example.text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
