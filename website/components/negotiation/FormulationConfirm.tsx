'use client';

import { useState } from 'react';
import type { FormulationReadyData } from '@/types/negotiation';
import styles from './FormulationConfirm.module.css';

interface FormulationConfirmProps {
  formulation: FormulationReadyData;
  onConfirm: (text: string) => void;
  disabled?: boolean;
}

export function FormulationConfirm({ formulation, onConfirm, disabled }: FormulationConfirmProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(formulation.formulated_text);

  const handleConfirm = () => {
    onConfirm(editing ? editText : formulation.formulated_text);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Enriched Demand</h3>
        <span className={styles.badge}>Review</span>
      </div>

      <div className={styles.original}>
        <span className={styles.label}>You said:</span>
        <p className={styles.originalText}>{formulation.raw_intent}</p>
      </div>

      <div className={styles.formulated}>
        <span className={styles.label}>We understood:</span>
        {editing ? (
          <textarea
            className={styles.editArea}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={5}
          />
        ) : (
          <p className={styles.formulatedText}>{formulation.formulated_text}</p>
        )}
      </div>

      {Object.keys(formulation.enrichments).length > 0 && (
        <div className={styles.enrichments}>
          {Array.isArray(formulation.enrichments.detected_skills) && (
            <div className={styles.tags}>
              {(formulation.enrichments.detected_skills as string[]).map((skill) => (
                <span key={skill} className={styles.tag}>{skill}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className={styles.actions}>
        <button
          className={styles.editButton}
          onClick={() => setEditing(!editing)}
          disabled={disabled}
        >
          {editing ? 'Cancel Edit' : 'Edit'}
        </button>
        <button
          className={styles.confirmButton}
          onClick={handleConfirm}
          disabled={disabled}
        >
          Confirm
        </button>
      </div>
    </div>
  );
}
