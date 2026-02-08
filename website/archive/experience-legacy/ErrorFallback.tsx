'use client';

import { ContentCard } from '@/components/ui/ContentCard';
import { Button } from '@/components/ui/Button';
import { handleApiError, ApiError } from '@/lib/errors';
import styles from './ErrorFallback.module.css';

interface ErrorFallbackProps {
  error?: Error | ApiError | null;
  title?: string;
  message?: string;
  onRetry?: () => void;
  onReset?: () => void;
  showDetails?: boolean;
}

/**
 * 错误回退组件
 * 显示用户友好的错误信息和操作按钮
 */
export function ErrorFallback({
  error,
  title,
  message,
  onRetry,
  onReset,
  showDetails = false,
}: ErrorFallbackProps) {
  // 处理错误，获取统一格式
  const apiError = error ? handleApiError(error) : null;

  const displayTitle = title || '出错了';
  const displayMessage = message || apiError?.message || '发生了未知错误，请稍后重试';

  return (
    <ContentCard className={styles.errorFallback}>
      <div className={styles.iconWrapper}>
        <svg
          className={styles.icon}
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
          <path
            d="M12 7v6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="12" cy="16" r="1" fill="currentColor" />
        </svg>
      </div>

      <h2 className={styles.title}>{displayTitle}</h2>
      <p className={styles.message}>{displayMessage}</p>

      {showDetails && apiError?.code && (
        <div className={styles.details}>
          <span className={styles.errorCode}>错误代码: {apiError.code}</span>
        </div>
      )}

      <div className={styles.actions}>
        {onRetry && (
          <Button variant="primary" onClick={onRetry}>
            重试
          </Button>
        )}
        {onReset && (
          <Button variant="outline" onClick={onReset}>
            返回首页
          </Button>
        )}
      </div>

      {showDetails && apiError?.details && process.env.NODE_ENV === 'development' && (
        <details className={styles.debugInfo}>
          <summary>调试信息</summary>
          <pre>{JSON.stringify(apiError.details, null, 2)}</pre>
        </details>
      )}
    </ContentCard>
  );
}

export default ErrorFallback;
