import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  Typography,
  Timeline,
  Space,
  Avatar,
  Tag,
  Empty,
  Button,
  Divider,
} from 'antd';
import {
  UserOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useEventStore } from '../../stores/eventStore';
import { useSSE } from '../../hooks/useSSE';
import { formatRelativeTime, getStatusColor } from '../../utils/format';
import Loading from '../../components/common/Loading';

const { Title, Text, Paragraph } = Typography;

export const NegotiationPage: React.FC = () => {
  const { negotiationId } = useParams<{ negotiationId: string }>();
  const {
    status,
    participants,
    proposals,
    timeline,
    isLoading,
    error,
    setNegotiationId,
  } = useEventStore();

  const { isConnected, connect, disconnect } = useSSE(negotiationId || null);

  useEffect(() => {
    if (negotiationId) {
      setNegotiationId(negotiationId);
    }
  }, [negotiationId, setNegotiationId]);

  if (isLoading) {
    return <Loading tip="加载协商进度..." />;
  }

  if (error) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical">
              <Text type="danger">{error}</Text>
              <Button type="primary" onClick={() => connect()}>
                重试连接
              </Button>
            </Space>
          }
        />
      </Card>
    );
  }

  const getStatusIcon = (s: string) => {
    switch (s) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'in_progress':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Space
        style={{
          width: '100%',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <Space>
          <Title level={2} style={{ margin: 0 }}>
            协商进度
          </Title>
          <Tag color={getStatusColor(status)}>{status}</Tag>
        </Space>
        <Space>
          <Tag color={isConnected ? 'green' : 'red'}>
            {isConnected ? '已连接' : '未连接'}
          </Tag>
          <Button onClick={isConnected ? disconnect : connect}>
            {isConnected ? '断开' : '重连'}
          </Button>
        </Space>
      </Space>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* 参与者 */}
        <Card title="参与者" size="small">
          {participants.length === 0 ? (
            <Empty description="暂无参与者" />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              {participants.map((p) => (
                <Space
                  key={p.agent_id}
                  style={{
                    padding: '8px 12px',
                    background: '#fafafa',
                    borderRadius: 8,
                    width: '100%',
                  }}
                >
                  <Avatar
                    icon={
                      p.agent_type === 'user' ? <UserOutlined /> : <RobotOutlined />
                    }
                    style={{
                      backgroundColor:
                        p.status === 'thinking' ? '#1890ff' : '#87d068',
                    }}
                  />
                  <div>
                    <Text strong>{p.display_name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {p.status === 'thinking' ? '思考中...' : p.agent_type}
                    </Text>
                  </div>
                </Space>
              ))}
            </Space>
          )}
        </Card>

        {/* 方案列表 */}
        <Card title="提出的方案" size="small">
          {proposals.length === 0 ? (
            <Empty description="暂无方案" />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              {proposals.map((proposal) => (
                <Card
                  key={proposal.id}
                  size="small"
                  style={{ marginBottom: 8 }}
                  extra={
                    <Tag
                      color={
                        proposal.status === 'accepted'
                          ? 'green'
                          : proposal.status === 'rejected'
                          ? 'red'
                          : 'blue'
                      }
                    >
                      {proposal.status}
                    </Tag>
                  }
                >
                  <Title level={5}>{proposal.content.title}</Title>
                  <Paragraph ellipsis={{ rows: 2 }}>
                    {proposal.content.description}
                  </Paragraph>
                  {proposal.content.price && (
                    <Text type="success">
                      ¥{proposal.content.price.amount}
                    </Text>
                  )}
                </Card>
              ))}
            </Space>
          )}
        </Card>
      </div>

      <Divider />

      {/* 时间线 */}
      <Card title="协商时间线">
        {timeline.length === 0 ? (
          <Empty description="协商尚未开始" />
        ) : (
          <Timeline
            items={timeline.map((event) => ({
              dot: getStatusIcon(event.event_type),
              children: (
                <div>
                  <Text strong>{event.event_type}</Text>
                  <br />
                  {event.content.message && (
                    <Paragraph>{event.content.message}</Paragraph>
                  )}
                  {event.content.thinking_step && (
                    <Text type="secondary">{event.content.thinking_step}</Text>
                  )}
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatRelativeTime(event.timestamp)}
                  </Text>
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </div>
  );
};

export default NegotiationPage;
