import React from 'react';
import { Card, Row, Col, Statistic, Typography, Empty } from 'antd';
import {
  CommentOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

export const DashboardPage: React.FC = () => {
  // TODO: Fetch real data from API
  const stats = {
    totalNegotiations: 0,
    completedNegotiations: 0,
    avgDuration: 0,
    activeAgents: 0,
  };

  return (
    <div>
      <Title level={2}>数据看板</Title>
      <Paragraph type="secondary">
        查看协商系统的整体运行情况和统计数据。
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总协商数"
              value={stats.totalNegotiations}
              prefix={<CommentOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completedNegotiations}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均耗时"
              value={stats.avgDuration}
              suffix="分钟"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃代理"
              value={stats.activeAgents}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 24 }}>
        <Empty description="暂无更多数据" />
      </Card>
    </div>
  );
};

export default DashboardPage;
