import React from 'react';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  ClockCircleOutlined,
  LogoutOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { CandidateDecision } from '../../types';

export interface CandidateStatusConfig {
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ReactNode;
  text: string;
  avatarBg: string;
}

interface CandidateStatusBadgeProps {
  decision?: CandidateDecision;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

/**
 * 获取候选人状态配置
 * @param decision 决策状态
 * @returns 状态配置对象
 */
export function getCandidateStatusConfig(decision?: CandidateDecision): CandidateStatusConfig {
  switch (decision) {
    case 'participate':
      return {
        color: 'var(--color-success)',
        bgColor: 'rgba(34, 197, 94, 0.1)',
        borderColor: 'rgba(34, 197, 94, 0.3)',
        icon: <CheckCircleOutlined />,
        text: '已接受',
        avatarBg: 'var(--color-success)',
      };
    case 'decline':
      return {
        color: 'var(--color-error)',
        bgColor: 'rgba(239, 68, 68, 0.1)',
        borderColor: 'rgba(239, 68, 68, 0.3)',
        icon: <CloseCircleOutlined />,
        text: '已拒绝',
        avatarBg: 'var(--color-error)',
      };
    case 'conditional':
      return {
        color: 'var(--color-warning)',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        borderColor: 'rgba(245, 158, 11, 0.3)',
        icon: <QuestionCircleOutlined />,
        text: '有条件',
        avatarBg: 'var(--color-warning)',
      };
    case 'withdrawn':
      return {
        color: 'var(--color-text-muted)',
        bgColor: 'rgba(163, 163, 163, 0.1)',
        borderColor: 'rgba(163, 163, 163, 0.3)',
        icon: <LogoutOutlined />,
        text: '已退出',
        avatarBg: 'var(--color-text-muted)',
      };
    case 'kicked':
      return {
        color: '#f97316', // orange-500
        bgColor: 'rgba(249, 115, 22, 0.1)',
        borderColor: 'rgba(249, 115, 22, 0.3)',
        icon: <StopOutlined />,
        text: '被踢出',
        avatarBg: '#f97316',
      };
    default:
      return {
        color: 'var(--color-info)',
        bgColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 0.3)',
        icon: <ClockCircleOutlined />,
        text: '待响应',
        avatarBg: 'var(--color-primary)',
      };
  }
}

/**
 * 候选人状态徽章组件
 * 用于展示候选人的参与状态（已接受/已拒绝/有条件/已退出/被踢出/待响应）
 */
const CandidateStatusBadge: React.FC<CandidateStatusBadgeProps> = ({
  decision,
  size = 'md',
  showIcon = true,
}) => {
  const config = getCandidateStatusConfig(decision);

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
  };

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full
        transition-all duration-200
        ${sizeClasses[size]}
      `}
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
    >
      {showIcon && (
        <span className="flex items-center" style={{ fontSize: size === 'sm' ? '10px' : '12px' }}>
          {config.icon}
        </span>
      )}
      <span>{config.text}</span>
    </span>
  );
};

export default CandidateStatusBadge;
