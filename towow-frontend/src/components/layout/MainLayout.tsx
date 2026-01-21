import React from 'react';
import { Layout, Menu, Typography, Space } from 'antd';
import {
  HomeOutlined,
  SendOutlined,
  CommentOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '首页',
  },
  {
    key: '/demand',
    icon: <SendOutlined />,
    label: '提交需求',
  },
  {
    key: '/negotiations',
    icon: <CommentOutlined />,
    label: '协商进度',
  },
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '数据看板',
  },
];

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <Space>
          <Title
            level={4}
            style={{
              color: '#fff',
              margin: 0,
              fontWeight: 600,
            }}
          >
            ToWow
          </Title>
          <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
            AI Negotiation Platform
          </span>
        </Space>
      </Header>
      <Layout>
        <Sider
          width={200}
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{
              height: '100%',
              borderRight: 0,
              paddingTop: 16,
            }}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
            style={{
              background: '#fff',
              padding: 24,
              margin: 0,
              minHeight: 280,
              borderRadius: 8,
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
