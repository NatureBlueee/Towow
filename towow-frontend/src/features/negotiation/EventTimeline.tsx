import React from 'react';
import { Card, Timeline, Empty, Tag, Typography } from 'antd';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  MessageOutlined,
  TeamOutlined,
  FileTextOutlined,
  BulbOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { TimelineEvent } from '../../types';
import { formatTime } from '../../utils/format';

const { Text } = Typography;

interface EventTimelineProps {
  events: TimelineEvent[];
  maxHeight?: number;
}

const EventTimeline: React.FC<EventTimelineProps> = ({ events, maxHeight = 400 }) => {
  const getEventLabel = (eventType: string): string => {
    const labels: Record<string, string> = {
      'towow.demand.understood': 'Demand Understood',
      'towow.demand.broadcast': 'Broadcast to Network',
      'towow.filter.completed': 'Filtering Complete',
      'towow.offer.submitted': 'Response Received',
      'towow.proposal.distributed': 'Proposal Distributed',
      'towow.proposal.feedback': 'Feedback Received',
      'towow.proposal.finalized': 'Negotiation Complete',
      'towow.negotiation.failed': 'Negotiation Failed',
      agent_thinking: 'Agent Thinking',
      agent_proposal: 'Proposal Submitted',
      agent_message: 'Message',
      status_update: 'Status Update',
      error: 'Error',
      negotiation_started: 'Started',
      agent_joined: 'Agent Joined',
      user_feedback: 'User Feedback',
      proposal_accepted: 'Proposal Accepted',
      proposal_rejected: 'Proposal Rejected',
      negotiation_completed: 'Completed',
    };
    return labels[eventType] || eventType.split('.').pop() || eventType;
  };

  const getEventIcon = (eventType: string) => {
    const iconStyle = { fontSize: '14px' };

    if (eventType.includes('finalized') || eventType.includes('completed') || eventType.includes('accepted')) {
      return <CheckCircleOutlined style={{ ...iconStyle, color: '#52c41a' }} />;
    }
    if (eventType.includes('failed') || eventType.includes('rejected') || eventType === 'error') {
      return <CloseCircleOutlined style={{ ...iconStyle, color: '#ff4d4f' }} />;
    }
    if (eventType.includes('proposal')) {
      return <FileTextOutlined style={{ ...iconStyle, color: '#722ed1' }} />;
    }
    if (eventType.includes('offer') || eventType.includes('feedback')) {
      return <MessageOutlined style={{ ...iconStyle, color: '#1890ff' }} />;
    }
    if (eventType.includes('filter') || eventType.includes('broadcast')) {
      return <TeamOutlined style={{ ...iconStyle, color: '#13c2c2' }} />;
    }
    if (eventType.includes('understood') || eventType.includes('thinking')) {
      return <BulbOutlined style={{ ...iconStyle, color: '#faad14' }} />;
    }
    if (eventType.includes('update') || eventType.includes('progress')) {
      return <SyncOutlined style={{ ...iconStyle, color: '#1890ff' }} spin />;
    }
    return <ExclamationCircleOutlined style={{ ...iconStyle, color: '#8c8c8c' }} />;
  };

  const getEventColor = (eventType: string): string => {
    if (eventType.includes('finalized') || eventType.includes('completed') || eventType.includes('accepted')) {
      return 'green';
    }
    if (eventType.includes('failed') || eventType.includes('rejected') || eventType === 'error') {
      return 'red';
    }
    if (eventType.includes('proposal')) {
      return 'purple';
    }
    if (eventType.includes('offer') || eventType.includes('feedback')) {
      return 'blue';
    }
    return 'gray';
  };

  const formatAgentName = (agentId?: string): string => {
    if (!agentId) return '';
    return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
  };

  // Reverse events to show newest first
  const reversedEvents = [...events].reverse();

  return (
    <Card
      title={
        <span>
          Event Stream{' '}
          <Tag color="blue">{events.length}</Tag>
        </span>
      }
      size="small"
      styles={{
        body: {
          padding: events.length === 0 ? '24px' : '16px',
          maxHeight: maxHeight,
          overflowY: 'auto',
        },
      }}
    >
      {events.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <LoadingOutlined style={{ fontSize: '24px', color: '#1890ff' }} spin />
              <span style={{ color: '#8c8c8c' }}>Waiting for events...</span>
            </div>
          }
        />
      ) : (
        <Timeline
          items={reversedEvents.map((event, idx) => ({
            dot: getEventIcon(event.event_type),
            color: getEventColor(event.event_type),
            children: (
              <div key={event.id || idx} style={{ paddingBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                  <Text strong style={{ fontSize: '13px' }}>
                    {getEventLabel(event.event_type)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: '11px', flexShrink: 0 }}>
                    {formatTime(event.timestamp)}
                  </Text>
                </div>
                {event.agent_id && (
                  <Tag style={{ marginTop: '4px', fontSize: '11px' }}>
                    {formatAgentName(event.agent_id)}
                  </Tag>
                )}
                {event.content?.message && (
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#595959',
                      marginTop: '4px',
                      padding: '8px',
                      backgroundColor: '#fafafa',
                      borderRadius: '4px',
                      borderLeft: `3px solid ${
                        event.event_type.includes('error') || event.event_type.includes('failed')
                          ? '#ff4d4f'
                          : '#1890ff'
                      }`,
                    }}
                  >
                    {event.content.message}
                  </div>
                )}
                {event.content?.thinking_step && (
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#8c8c8c',
                      fontStyle: 'italic',
                      marginTop: '4px',
                    }}
                  >
                    {event.content.thinking_step}
                  </div>
                )}
                {event.content?.error && (
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#ff4d4f',
                      marginTop: '4px',
                      padding: '8px',
                      backgroundColor: '#fff2f0',
                      borderRadius: '4px',
                      border: '1px solid #ffccc7',
                    }}
                  >
                    {event.content.error}
                  </div>
                )}
              </div>
            ),
          }))}
        />
      )}
    </Card>
  );
};

export default EventTimeline;
