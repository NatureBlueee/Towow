'use client';

import { useState, useEffect } from 'react';
import styles from './MessageBubble.module.css';

interface NegotiationMessage {
  message_id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  message_type: 'text' | 'system' | 'action';
  content: string;
  timestamp: string;
}

interface MessageBubbleProps {
  message: NegotiationMessage;
  isCurrentUser?: boolean;
  enableTypewriter?: boolean;
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 打字机效果 Hook
function useTypewriter(text: string, enabled: boolean, speed: number = 20) {
  const [displayedText, setDisplayedText] = useState(enabled ? '' : text);
  const [isTyping, setIsTyping] = useState(enabled);

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(text);
      setIsTyping(false);
      return;
    }

    setDisplayedText('');
    setIsTyping(true);
    let index = 0;

    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, enabled, speed]);

  return { displayedText, isTyping };
}

export function MessageBubble({
  message,
  isCurrentUser = false,
  enableTypewriter = true,
}: MessageBubbleProps) {
  // 只对最新消息启用打字机效果（通过 enableTypewriter 控制）
  const { displayedText, isTyping } = useTypewriter(
    message.content,
    enableTypewriter && message.message_type !== 'system',
    15 // 打字速度（毫秒/字符）
  );

  const bubbleClass = [
    styles.bubble,
    styles[message.message_type],
    isCurrentUser ? styles.currentUser : '',
  ].filter(Boolean).join(' ');

  // System messages have different layout
  if (message.message_type === 'system') {
    return (
      <div className={bubbleClass}>
        <div className={styles.systemContent}>{message.content}</div>
        <span className={styles.systemTime}>{formatTime(message.timestamp)}</span>
      </div>
    );
  }

  return (
    <div className={bubbleClass}>
      <div className={styles.header}>
        <div className={styles.avatar}>
          {message.sender_name.charAt(0).toUpperCase()}
        </div>
        <span className={styles.name}>{message.sender_name}</span>
        <span className={styles.time}>{formatTime(message.timestamp)}</span>
      </div>
      <div className={styles.content}>
        {displayedText}
        {isTyping && <span className={styles.cursor}>|</span>}
      </div>
    </div>
  );
}
