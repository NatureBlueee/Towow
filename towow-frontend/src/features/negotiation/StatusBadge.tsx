import React from 'react';
import { Tag, Tooltip, Space } from 'antd';
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

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  isConnected,
  reconnectAttempts = 0,
}) => {
  const getConnectionStatus = () => {
    if (isConnected) {
      return {
        color: 'success' as const,
        icon: <CheckCircleOutlined />,
        text: 'Connected',
        tooltip: 'Real-time connection established',
      };
    }
    if (reconnectAttempts > 0) {
      return {
        color: 'warning' as const,
        icon: <SyncOutlined spin />,
        text: `Reconnecting (${reconnectAttempts})`,
        tooltip: `Attempting to reconnect... (attempt ${reconnectAttempts})`,
      };
    }
    return {
      color: 'error' as const,
      icon: <DisconnectOutlined />,
      text: 'Disconnected',
      tooltip: 'Connection lost',
    };
  };

  const getNegotiationStatus = () => {
    const statusConfig: Record<
      NegotiationStatus,
      { color: string; icon: React.ReactNode; text: string; tooltip: string }
    > = {
      pending: {
        color: 'default',
        icon: <ClockCircleOutlined />,
        text: 'Pending',
        tooltip: 'Waiting to start',
      },
      connecting: {
        color: 'processing',
        icon: <LoadingOutlined spin />,
        text: 'Connecting',
        tooltip: 'Establishing connection...',
      },
      filtering: {
        color: 'processing',
        icon: <FilterOutlined />,
        text: 'Filtering',
        tooltip: 'Finding suitable candidates...',
      },
      collecting: {
        color: 'processing',
        icon: <TeamOutlined />,
        text: 'Collecting',
        tooltip: 'Collecting responses from candidates...',
      },
      aggregating: {
        color: 'processing',
        icon: <SyncOutlined spin />,
        text: 'Aggregating',
        tooltip: 'Generating collaboration proposal...',
      },
      negotiating: {
        color: 'purple',
        icon: <FileTextOutlined />,
        text: 'Negotiating',
        tooltip: 'Active negotiation in progress',
      },
      finalized: {
        color: 'success',
        icon: <TrophyOutlined />,
        text: 'Finalized',
        tooltip: 'Negotiation completed successfully',
      },
      failed: {
        color: 'error',
        icon: <CloseCircleOutlined />,
        text: 'Failed',
        tooltip: 'Negotiation failed',
      },
      in_progress: {
        color: 'processing',
        icon: <LoadingOutlined spin />,
        text: 'In Progress',
        tooltip: 'Negotiation in progress',
      },
      awaiting_user: {
        color: 'warning',
        icon: <ExclamationCircleOutlined />,
        text: 'Awaiting User',
        tooltip: 'Waiting for user input',
      },
      completed: {
        color: 'success',
        icon: <CheckCircleOutlined />,
        text: 'Completed',
        tooltip: 'Negotiation completed',
      },
      cancelled: {
        color: 'default',
        icon: <CloseCircleOutlined />,
        text: 'Cancelled',
        tooltip: 'Negotiation cancelled',
      },
    };

    return statusConfig[status] || statusConfig.pending;
  };

  const connectionStatus = getConnectionStatus();
  const negotiationStatus = getNegotiationStatus();

  return (
    <Space size="small">
      <Tooltip title={connectionStatus.tooltip}>
        <Tag color={connectionStatus.color} icon={connectionStatus.icon}>
          {connectionStatus.text}
        </Tag>
      </Tooltip>
      <Tooltip title={negotiationStatus.tooltip}>
        <Tag color={negotiationStatus.color} icon={negotiationStatus.icon}>
          {negotiationStatus.text}
        </Tag>
      </Tooltip>
    </Space>
  );
};

export default StatusBadge;
