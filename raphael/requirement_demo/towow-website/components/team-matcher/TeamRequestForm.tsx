'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { TagInput } from './TagInput';
import {
  SKILL_OPTIONS,
  ROLE_OPTIONS,
  AVAILABILITY_OPTIONS,
  TeamRequestFormData,
} from '@/lib/team-matcher/types';
import { createTeamRequest } from '@/lib/team-matcher/api';
import styles from './TeamRequestForm.module.css';

export function TeamRequestForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<TeamRequestFormData>({
    project_idea: '',
    skills: [],
    available_time: '',
    roles_needed: [],
  });

  const isValid =
    formData.project_idea.trim().length > 10 &&
    formData.skills.length > 0 &&
    formData.available_time !== '';

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || isSubmitting) return;

      setIsSubmitting(true);
      try {
        const response = await createTeamRequest({
          ...formData,
          user_id: 'demo-user', // TODO: replace with real user
        });
        router.push(`/team/progress/${response.request_id}`);
      } catch (err) {
        console.error('Failed to create team request:', err);
        setIsSubmitting(false);
      }
    },
    [formData, isValid, isSubmitting, router]
  );

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <i className="ri-signal-tower-line" />
        </div>
        <h1 className={styles.title}>发出你的信号</h1>
        <p className={styles.subtitle}>
          描述你的项目想法和你能带来的技能，让共振找到你的伙伴
        </p>
      </div>

      {/* Project Idea */}
      <div className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="project-idea">
          <i className="ri-lightbulb-line" />
          项目想法
        </label>
        <textarea
          id="project-idea"
          className={styles.textarea}
          placeholder="描述你想做的项目... 比如：一个用 AI 分析饮食数据并给出个性化健康建议的应用"
          value={formData.project_idea}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, project_idea: e.target.value }))
          }
          maxLength={500}
          rows={4}
        />
        <div className={styles.charCount}>
          <span>{formData.project_idea.length}</span> / 500
        </div>
      </div>

      {/* My Skills */}
      <div className={styles.field}>
        <div className={styles.fieldLabelRow}>
          <i className="ri-tools-line" />
          <span>我的技能</span>
        </div>
        <TagInput
          label=""
          value={formData.skills}
          onChange={(skills) => setFormData((prev) => ({ ...prev, skills }))}
          suggestions={SKILL_OPTIONS}
          placeholder="选择或输入你的技能..."
          maxTags={8}
          hint="选择你擅长的技能，团队组合时会用到"
        />
      </div>

      {/* Available Time */}
      <div className={styles.field}>
        <label className={styles.fieldLabel}>
          <i className="ri-time-line" />
          可用时间
        </label>
        <div className={styles.radioGroup}>
          {AVAILABILITY_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`${styles.radioCard} ${
                formData.available_time === opt.value ? styles.radioCardActive : ''
              }`}
            >
              <input
                type="radio"
                name="available_time"
                value={opt.value}
                checked={formData.available_time === opt.value}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    available_time: e.target.value,
                  }))
                }
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Roles Needed */}
      <div className={styles.field}>
        <div className={styles.fieldLabelRow}>
          <i className="ri-group-line" />
          <span>我在找</span>
          <span className={styles.fieldHint}>不确定也没关系</span>
        </div>
        <TagInput
          label=""
          value={formData.roles_needed}
          onChange={(roles_needed) =>
            setFormData((prev) => ({ ...prev, roles_needed }))
          }
          suggestions={ROLE_OPTIONS}
          placeholder="期望的队友角色（可选）..."
          maxTags={5}
          hint="留空也可以，系统会帮你发现意想不到的组合"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        className={`${styles.submitBtn} ${isValid ? styles.submitBtnReady : ''}`}
        disabled={!isValid || isSubmitting}
      >
        {isSubmitting ? (
          <>
            <span className={styles.submitSpinner} />
            信号发送中...
          </>
        ) : (
          <>
            <i className="ri-radar-line" />
            发出信号
          </>
        )}
      </button>

      <p className={styles.submitHint}>
        信号发出后，系统会广播给网络中的所有 Agent，等待它们的响应
      </p>
    </form>
  );
}
