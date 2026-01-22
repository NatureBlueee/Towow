import React from 'react';
import { Card, Avatar, Tag, Empty, Tooltip } from 'antd';
import { UserOutlined, CheckCircleOutlined, CloseCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type { Candidate, TimelineEvent } from '../../types';

interface CandidateListProps {
  candidates: Candidate[];
  events: TimelineEvent[];
}

const CandidateList: React.FC<CandidateListProps> = ({ candidates, events }) => {
  // Extract responses from events
  const getResponse = (agentId: string): Candidate['response'] | undefined => {
    const responseEvent = events.find(
      (e) =>
        (e.event_type === 'towow.offer.submitted' || e.event_type === 'agent_proposal') &&
        e.agent_id === agentId
    );
    if (responseEvent) {
      // Try to extract from metadata or content
      const metadata = responseEvent.metadata as Record<string, unknown> | undefined;
      if (metadata?.decision) {
        return {
          decision: metadata.decision as 'participate' | 'decline' | 'conditional',
          contribution: metadata.contribution as string | undefined,
        };
      }
    }
    return undefined;
  };

  const getDecisionColor = (decision?: string) => {
    switch (decision) {
      case 'participate':
        return 'success';
      case 'decline':
        return 'error';
      case 'conditional':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getDecisionIcon = (decision?: string) => {
    switch (decision) {
      case 'participate':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'decline':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'conditional':
        return <QuestionCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  const getDecisionText = (decision?: string) => {
    switch (decision) {
      case 'participate':
        return 'Willing to participate';
      case 'decline':
        return 'Declined';
      case 'conditional':
        return 'Conditional';
      default:
        return 'Waiting for response';
    }
  };

  const formatAgentName = (agentId: string) => {
    return agentId.replace('user_agent_', '').replace(/_/g, ' ').toUpperCase();
  };

  return (
    <Card
      title={
        <span>
          Candidates{' '}
          <Tag color="blue">{candidates.length}</Tag>
        </span>
      }
      size="small"
      styles={{ body: { padding: candidates.length === 0 ? '24px' : '12px' } }}
    >
      {candidates.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Waiting for candidates..."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {candidates.map((candidate) => {
            const response = candidate.response || getResponse(candidate.agent_id);
            const decision = response?.decision;

            return (
              <div
                key={candidate.agent_id}
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: `2px solid ${
                    decision === 'participate'
                      ? '#b7eb8f'
                      : decision === 'decline'
                      ? '#ffccc7'
                      : decision === 'conditional'
                      ? '#ffe58f'
                      : '#d9d9d9'
                  }`,
                  backgroundColor:
                    decision === 'participate'
                      ? '#f6ffed'
                      : decision === 'decline'
                      ? '#fff2f0'
                      : decision === 'conditional'
                      ? '#fffbe6'
                      : '#fafafa',
                  transition: 'all 0.3s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <Avatar
                    icon={<UserOutlined />}
                    style={{
                      backgroundColor:
                        decision === 'participate'
                          ? '#52c41a'
                          : decision === 'decline'
                          ? '#ff4d4f'
                          : decision === 'conditional'
                          ? '#faad14'
                          : '#1890ff',
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: '#262626' }}>
                        {formatAgentName(candidate.agent_id)}
                      </span>
                      {decision && (
                        <Tooltip title={getDecisionText(decision)}>
                          <Tag
                            color={getDecisionColor(decision)}
                            icon={getDecisionIcon(decision)}
                            style={{ marginRight: 0 }}
                          >
                            {decision === 'participate'
                              ? 'Yes'
                              : decision === 'decline'
                              ? 'No'
                              : 'Maybe'}
                          </Tag>
                        </Tooltip>
                      )}
                    </div>
                    <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                      {candidate.reason}
                    </div>
                    {response?.contribution && (
                      <div
                        style={{
                          fontSize: '12px',
                          color: '#595959',
                          fontStyle: 'italic',
                          marginTop: '8px',
                          padding: '8px',
                          backgroundColor: 'rgba(0, 0, 0, 0.02)',
                          borderRadius: '4px',
                          borderLeft: '3px solid #1890ff',
                        }}
                      >
                        "{response.contribution}"
                      </div>
                    )}
                    {response?.conditions && response.conditions.length > 0 && (
                      <div style={{ marginTop: '8px' }}>
                        <span style={{ fontSize: '11px', color: '#8c8c8c' }}>Conditions:</span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                          {response.conditions.map((condition, idx) => (
                            <Tag key={idx} style={{ fontSize: '11px' }}>
                              {condition}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};

export default CandidateList;
