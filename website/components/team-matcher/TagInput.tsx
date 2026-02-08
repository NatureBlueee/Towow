'use client';

import { useState, useRef, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import styles from './TagInput.module.css';

interface TagInputProps {
  /** Current selected tags */
  value: string[];
  /** Callback when tags change */
  onChange: (tags: string[]) => void;
  /** Predefined suggestions */
  suggestions: readonly string[];
  /** Placeholder text */
  placeholder?: string;
  /** Maximum number of tags */
  maxTags?: number;
  /** Label text */
  label: string;
  /** Hint text below the input */
  hint?: string;
}

export function TagInput({
  value,
  onChange,
  suggestions,
  placeholder,
  maxTags = 10,
  label,
  hint,
}: TagInputProps) {
  const t = useTranslations('TeamMatcher.tagInput');
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const resolvedPlaceholder = placeholder || t('defaultPlaceholder');

  const filteredSuggestions = suggestions.filter(
    (s) =>
      !value.includes(s) &&
      s.toLowerCase().includes(inputValue.toLowerCase())
  );

  const addTag = useCallback(
    (tag: string) => {
      const trimmed = tag.trim();
      if (trimmed && !value.includes(trimmed) && value.length < maxTags) {
        onChange([...value, trimmed]);
      }
      setInputValue('');
      setShowSuggestions(false);
    },
    [value, onChange, maxTags]
  );

  const removeTag = useCallback(
    (tag: string) => {
      onChange(value.filter((t) => t !== tag));
    },
    [value, onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputValue.trim()) {
        addTag(inputValue);
      }
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      removeTag(value[value.length - 1]);
    }
  };

  return (
    <div className={styles.wrapper}>
      <label className={styles.label}>{label}</label>

      <div
        className={styles.inputArea}
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((tag) => (
          <span key={tag} className={styles.tag}>
            <span className={styles.tagText}>{tag}</span>
            <button
              type="button"
              className={styles.tagRemove}
              onClick={(e) => {
                e.stopPropagation();
                removeTag(tag);
              }}
              aria-label={`Remove ${tag}`}
            >
              <i className="ri-close-line" />
            </button>
          </span>
        ))}
        {value.length < maxTags && (
          <input
            ref={inputRef}
            type="text"
            className={styles.input}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => {
              // Delay to allow suggestion click
              setTimeout(() => setShowSuggestions(false), 200);
            }}
            onKeyDown={handleKeyDown}
            placeholder={value.length === 0 ? resolvedPlaceholder : ''}
          />
        )}
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && inputValue && filteredSuggestions.length > 0 && (
        <div className={styles.suggestions}>
          {filteredSuggestions.slice(0, 8).map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className={styles.suggestionItem}
              onMouseDown={(e) => {
                e.preventDefault();
                addTag(suggestion);
              }}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {/* Quick select chips when input is empty */}
      {!inputValue && filteredSuggestions.length > 0 && value.length < maxTags && (
        <div className={styles.quickChips}>
          {filteredSuggestions.slice(0, 6).map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className={styles.chip}
              onClick={() => addTag(suggestion)}
            >
              {suggestion}
            </button>
          ))}
          {filteredSuggestions.length > 6 && (
            <span className={styles.moreHint}>
              {t('moreItems', { count: filteredSuggestions.length - 6 })}
            </span>
          )}
        </div>
      )}

      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
