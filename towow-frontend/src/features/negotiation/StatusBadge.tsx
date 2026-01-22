import React from 'react';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  DisconnectOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  FilterOutlined,
  TeamOutlined,
  FileTextOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import type { NegotiationStatus } from '../../types';

interface StatusBadgeProps {
  status: NegotiationStatus;
  isConnected: boolean;
  reconnectAttempts?: number;
}

interface StatusConfig {
  color: string;
  bgColor: string;
  icon: React.ReactNode;
  text: string;
  tooltip: string;
  pulse?: boolean;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  isConnected,
  reconnectAttempts = 0,
}) => {
  const getConnectionStatus = (): StatusConfig => {
    if (isConnected) {
      return {
        color: 'var(--color-success)',
        bgColor: 'rgba(34, 197, 94, 0.1)',
        icon: <CheckCircleOutlined />,
        text: '已连接',
        tooltip: '实时连接已建立',
        pulse: true,
      };
    }
    if (reconnectAttempts > 0) {
      return {
        color: 'var(--color-warning)',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        icon: <SyncOutlined className="animate-spin" />,
        text: `重连中 (${reconnectAttempts})`,
        tooltip: `正在尝试重新连接...（第 ${reconnectAttempts} 次）`,
      };
    }
    return {
      color: 'var(--color-error)',
      bgColor: 'rgba(239, 68, 68, 0.1)',
      icon: <DisconnectOutlined />,
      text: '已断开',
      tooltip: '连接已断开',
    };
  };

  const getNegotiationStatus = (): StatusConfig => {
    const statusConfig: Record<NegotiationStatus, StatusConfig> = {
      pending: {
        color: 'var(--color-text-secondary)',
        bgColor: 'var(--color-bg-muted)',
        icon: <ClockCircleOutlined />,
        text: '准备中',
        tooltip: '等待开始',
      },
      connecting: {
        color: 'var(--color-primary)',
        bgColor: 'rgba(99, 102, 241, 0.1)',
        icon: <LoadingOutlined className="animate-spin" />,
        text: '连接中',
        tooltip: '正在建立连接...',
        pulse: true,
      },
      filtering: {
        color: 'var(--color-info)',
        bgColor: 'rgba(59, 130, 246, 0.1)',
        icon: <FilterOutlined />,
        text: '筛选中',
        tooltip: '正在寻找合适的候选人...',
        pulse: true,
      },
      collecting: {
        color: 'var(--color-info)',
        bgColor: 'rgba(59, 130, 246, 0.1)',
        icon: <TeamOutlined />,
        text: '收集中',
        tooltip: '正在收集候选人响应...',
        pulse: true,
      },
      aggregating: {
        color: 'var(--color-primary)',
        bgColor: 'rgba(99, 102, 241, 0.1)',
        icon: <SyncOutlined className="animate-spin" />,
        text: '聚合中',
        tooltip: '正在生成协作方案...',
        pulse: true,
      },
      negotiating: {
        color: 'var(--color-secondary)',
        bgColor: 'rgba(139, 92, 246, 0.1)',
        icon: <FileTextOutlined />,
        text: '协商中',
        tooltip: '协商正在进行中',
        pulse: true,
      },
      finalized: {
        color: 'var(--color-success)',
        bgColor: 'rgba(34, 197, 94, 0.1)',
        icon: <TrophyOutlined />,
        text: '已完成',
        tooltip: '协商成功完成',
      },
      failed: {
        color: 'var(--color-error)',
        bgColor: 'rgba(239, 68, 68, 0.1)',
        icon: <CloseCircleOutlined />,
        text: '失败',
        tooltip: '协商失败',
      },
      in_progress: {
        color: 'var(--color-primary)',
        bgColor: 'rgba(99, 102, 241, 0.1)',
        icon: <LoadingOutlined className="animate-spin" />,
        text: '进行中',
        tooltip: '协商进行中',
        pulse: true,
      },
      awaiting_user: {
        color: 'var(--color-warning)',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        icon: <ExclamationCircleOutlined />,
        text: '等待用户',
        tooltip: '等待用户输入',
        pulse: true,
      },
      completed: {
        color: 'var(--color-success)',
        bgColor: 'rgba(34, 197, 94, 0.1)',
        icon: <CheckCircleOutlined />,
        text: '已完成',
        tooltip: '协商已完成',
      },
      cancelled: {
        color: 'var(--color-text-muted)',
        bgColor: 'var(--color-bg-muted)',
        icon: <CloseCircleOutlined />,
        text: '已取消',
        tooltip: '协商已取消',
      },
    };

    return statusConfig[status] || statusConfig.pending;
  };

  const connectionStatus = getConnectionStatus();
  const negotiationStatus = getNegotiationStatus();

  const Badge: React.FC<{ config: StatusConfig }> = ({ config }) => (
    <div
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200"
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
      title={config.tooltip}
    >
      {config.pulse && (
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ backgroundColor: config.color }}
        />
      )}
      <span className="flex items-center" style={{ fontSize: '12px' }}>
        {config.icon}
      </span>
      <span>{config.text}</span>
    </div>
  );

  return (
    <div className="flex items-center gap-2">
      <Badge config={connectionStatus} />
      <Badge config={negotiationStatus} />
    </div>
  );
};

export default StatusBadge;
