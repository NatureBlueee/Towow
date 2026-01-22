import React, { useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Typography,
  Space,
  Button,
  Divider,
  Row,
  Col,
  Alert,
  Statistic,
  Progress,
} from 'antd';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  DisconnectOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useEventStore } from '../../stores/eventStore';
import { useSSE } from '../../hooks/useSSE';
import CandidateList from './CandidateList';
import ProposalCard from './ProposalCard';
import EventTimeline from './EventTimeline';
import StatusBadge from './StatusBadge';
import Loading from '../../components/common/Loading';
import type { SSEEvent } from '../../types';

const { Title, Text, Paragraph } = Typography;

export const NegotiationPage: React.FC = () => {
  const { negotiationId } = useParams<{ negotiationId: string }>();
  const navigate = useNavigate();

  const {
    status,
    candidates,
    currentProposal,
    currentRound,
    timeline,
    isLoading,
    error,
    setNegotiationId,
    handleSSEEvent,
    reset,
  } = useEventStore();

  // Memoize the event handler to prevent unnecessary reconnections
  const onSSEEvent = useCallback(
    (event: SSEEvent) => {
      handleSSEEvent(event);
    },
    [handleSSEEvent]
  );

  const onSSEError = useCallback((err: Error) => {
    console.error('SSE Error:', err);
  }, []);

  const { isConnected, connect, disconnect, reconnectAttempts } = useSSE(
    negotiationId || null,
    {
      onEvent: onSSEEvent,
      onError: onSSEError,
    }
  );

  useEffect(() => {
    if (negotiationId) {
      setNegotiationId(negotiationId);
    }

    return () => {
      // Clean up on unmount
      reset();
    };
  }, [negotiationId, setNegotiationId, reset]);

  // Calculate statistics
  const participatingCount = candidates.filter(
    (c) => c.response?.decision === 'participate'
  ).length;
  const pendingCount = candidates.filter((c) => !c.response).length;

  const getStatusDescription = () => {
    const descriptions: Record<string, string> = {
      pending: 'Initializing negotiation...',
      connecting: 'Connecting to negotiation network...',
      filtering: 'AI is finding suitable candidates for your request...',
      collecting: 'Collecting responses from potential collaborators...',
      aggregating: 'Generating optimal collaboration proposal...',
      negotiating: `Active negotiation in progress (Round ${currentRound})`,
      finalized: 'Negotiation completed! Your collaboration plan is ready.',
      failed: 'Unfortunately, the negotiation could not reach an agreement.',
      in_progress: 'Negotiation is in progress...',
      awaiting_user: 'Waiting for your input to continue...',
      completed: 'Negotiation has been completed.',
      cancelled: 'Negotiation was cancelled.',
    };
    return descriptions[status] || 'Processing...';
  };

  const getProgressPercent = () => {
    const stages: Record<string, number> = {
      pending: 0,
      connecting: 10,
      filtering: 30,
      collecting: 50,
      aggregating: 70,
      negotiating: 80,
      finalized: 100,
      completed: 100,
      failed: 100,
      cancelled: 100,
    };
    return stages[status] || 0;
  };

  const getProgressStatus = () => {
    if (status === 'finalized' || status === 'completed') return 'success';
    if (status === 'failed') return 'exception';
    return 'active';
  };

  if (isLoading) {
    return <Loading tip="Loading negotiation..." />;
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/demand')}
            >
              Back
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              Negotiation Progress
            </Title>
          </Space>
          <Space>
            <StatusBadge
              status={status}
              isConnected={isConnected}
              reconnectAttempts={reconnectAttempts}
            />
            <Button
              icon={isConnected ? <DisconnectOutlined /> : <ReloadOutlined />}
              onClick={isConnected ? disconnect : connect}
            >
              {isConnected ? 'Disconnect' : 'Reconnect'}
            </Button>
          </Space>
        </Space>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          closable
          style={{ marginBottom: 24 }}
          action={
            <Button size="small" type="primary" onClick={connect}>
              Retry
            </Button>
          }
        />
      )}

      {/* Status Overview Card */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={24} align="middle">
          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                NEGOTIATION ID
              </Text>
              <br />
              <Text code copyable style={{ fontSize: 12 }}>
                {negotiationId}
              </Text>
            </div>
            <Paragraph style={{ color: '#595959', marginBottom: 0 }}>
              {getStatusDescription()}
            </Paragraph>
          </Col>
          <Col span={12}>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">Progress</Text>
            </div>
            <Progress
              percent={getProgressPercent()}
              status={getProgressStatus()}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </Col>
        </Row>
      </Card>

      {/* Statistics Row */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Candidates"
              value={candidates.length}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Participating"
              value={participatingCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Pending Response"
              value={pendingCount}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Current Round"
              value={currentRound}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Grid */}
      <Row gutter={24}>
        {/* Left: Candidates */}
        <Col xs={24} lg={8}>
          <CandidateList candidates={candidates} events={timeline} />
        </Col>

        {/* Center: Proposal */}
        <Col xs={24} lg={8}>
          <ProposalCard
            proposal={currentProposal}
            status={status}
            round={currentRound}
          />
        </Col>

        {/* Right: Event Timeline */}
        <Col xs={24} lg={8}>
          <EventTimeline events={timeline} maxHeight={500} />
        </Col>
      </Row>

      {/* Action Buttons for Finalized State */}
      {status === 'finalized' && currentProposal && (
        <>
          <Divider />
          <Card>
            <div style={{ textAlign: 'center' }}>
              <Title level={4} style={{ color: '#52c41a' }}>
                <CheckCircleOutlined /> Negotiation Complete!
              </Title>
              <Paragraph type="secondary">
                Your collaboration plan has been finalized. You can now proceed
                with the proposed arrangement.
              </Paragraph>
              <Space size="large">
                <Button type="primary" size="large">
                  Accept & Proceed
                </Button>
                <Button size="large">Save for Later</Button>
                <Button size="large" onClick={() => navigate('/demand')}>
                  Start New Negotiation
                </Button>
              </Space>
            </div>
          </Card>
        </>
      )}

      {/* Failed State Actions */}
      {status === 'failed' && (
        <>
          <Divider />
          <Card>
            <div style={{ textAlign: 'center' }}>
              <Title level={4} type="danger">
                Negotiation Could Not Complete
              </Title>
              <Paragraph type="secondary">
                The negotiation process could not reach a successful agreement.
                You can try again with adjusted requirements.
              </Paragraph>
              <Space size="large">
                <Button type="primary" size="large" onClick={() => navigate('/demand')}>
                  Try Again
                </Button>
                <Button size="large">Contact Support</Button>
              </Space>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

export default NegotiationPage;
