'use client';

import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import styles from './LoginPanel.module.css';

interface LoginPanelProps {
  onLoginClick: () => void;
  isLoading?: boolean;
}

export function LoginPanel({ onLoginClick, isLoading = false }: LoginPanelProps) {
  return (
    <ContentCard className={styles.loginPanel}>
      <div className={styles.icon}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
          <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </div>
      <h2 className={styles.title}>体验 ToWow Agent 协作</h2>
      <p className={styles.description}>
        通过 SecondMe 登录，提交您的协作需求，<br/>
        观看 AI Agent 如何为您协商解决方案。
      </p>
      <Button
        variant="primary"
        onClick={onLoginClick}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className={styles.spinner} />
            登录中...
          </>
        ) : (
          '使用 SecondMe 登录'
        )}
      </Button>
      <p className={styles.hint}>
        首次登录将自动创建您的 Agent 身份
      </p>
    </ContentCard>
  );
}
