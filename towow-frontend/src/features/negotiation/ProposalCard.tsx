import React from 'react';
import { Card, Tag, Empty, Progress, Avatar, Tooltip } from 'antd';
import {
  UserOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import type { ToWowProposal, NegotiationStatus } from '../../types';

interface ProposalCardProps {
  proposal: ToWowProposal | null;
  status: NegotiationStatus;
  round: number;
}

const ProposalCard: React.FC<ProposalCardProps> = ({ proposal, status, round }) => {
  const getConfidenceColor = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return 'success';
      case 'medium':
        return 'warning';
      case 'low':
        return 'error';
      default:
        return 'default';
    }
  };

  const getConfidenceText = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return 'High Confidence';
      case 'medium':
        return 'Medium Confidence';
      case 'low':
        return 'Low Confidence';
      default:
        return 'Unknown';
    }
  };

  const getConfidencePercent = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return 90;
      case 'medium':
        return 60;
      case 'low':
        return 30;
      default:
        return 0;
    }
  };

  const formatAgentName = (agentId: string) => {
    return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
  };

  const isLoading = !proposal && !['finalized', 'failed', 'completed', 'cancelled'].includes(status);

  return (
    <Card
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>
            {status === 'finalized' ? (
              <>
                <TrophyOutlined style={{ color: '#52c41a', marginRight: '8px' }} />
                Final Proposal
              </>
            ) : (
              'Collaboration Proposal'
            )}
          </span>
          {round > 0 && (
            <Tag color="purple">Round {round}</Tag>
          )}
        </div>
      }
      size="small"
      styles={{
        body: {
          padding: proposal ? '16px' : '24px',
        },
      }}
    >
      {!proposal ? (
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <LoadingOutlined style={{ fontSize: '32px', color: '#1890ff' }} spin />
              <span style={{ color: '#8c8c8c' }}>Generating proposal...</span>
            </div>
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                status === 'failed' ? 'Negotiation failed' : 'No proposal yet'
              }
            />
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Summary */}
          <div
            style={{
              padding: '16px',
              backgroundColor: status === 'finalized' ? '#f6ffed' : '#f0f5ff',
              borderRadius: '8px',
              borderLeft: `4px solid ${status === 'finalized' ? '#52c41a' : '#1890ff'}`,
            }}
          >
            <div
              style={{
                fontWeight: 500,
                color: status === 'finalized' ? '#389e0d' : '#1890ff',
                lineHeight: 1.6,
              }}
            >
              {proposal.summary}
            </div>
          </div>

          {/* Assignments */}
          {proposal.assignments && proposal.assignments.length > 0 && (
            <div>
              <div
                style={{
                  fontSize: '13px',
                  fontWeight: 500,
                  color: '#595959',
                  marginBottom: '8px',
                }}
              >
                Task Assignments
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {proposal.assignments.map((assignment, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px',
                      backgroundColor: '#fafafa',
                      borderRadius: '8px',
                      border: '1px solid #f0f0f0',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                        <span style={{ fontWeight: 500, color: '#262626' }}>
                          {formatAgentName(assignment.agent_id)}
                        </span>
                      </div>
                      <Tag color="purple" style={{ marginRight: 0 }}>
                        {assignment.role}
                      </Tag>
                    </div>
                    <div style={{ fontSize: '12px', color: '#595959' }}>
                      {assignment.responsibility}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timeline */}
          {proposal.timeline && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px',
                backgroundColor: '#fafafa',
                borderRadius: '8px',
              }}
            >
              <ClockCircleOutlined style={{ color: '#1890ff' }} />
              <span style={{ fontSize: '13px', color: '#595959' }}>
                <strong>Timeline:</strong> {proposal.timeline}
              </span>
            </div>
          )}

          {/* Confidence */}
          {proposal.confidence && (
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '4px',
                }}
              >
                <span style={{ fontSize: '12px', color: '#8c8c8c' }}>Confidence Level</span>
                <Tooltip title={getConfidenceText(proposal.confidence)}>
                  <Tag color={getConfidenceColor(proposal.confidence)}>
                    {proposal.confidence.toUpperCase()}
                  </Tag>
                </Tooltip>
              </div>
              <Progress
                percent={getConfidencePercent(proposal.confidence)}
                showInfo={false}
                strokeColor={
                  proposal.confidence === 'high'
                    ? '#52c41a'
                    : proposal.confidence === 'medium'
                    ? '#faad14'
                    : '#ff4d4f'
                }
                size="small"
              />
            </div>
          )}

          {/* Status indicator for finalized */}
          {status === 'finalized' && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '12px',
                backgroundColor: '#f6ffed',
                borderRadius: '8px',
                border: '1px solid #b7eb8f',
              }}
            >
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
              <span style={{ color: '#52c41a', fontWeight: 500 }}>
                Negotiation Complete
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default ProposalCard;
