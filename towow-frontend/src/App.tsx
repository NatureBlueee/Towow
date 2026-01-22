import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/layout/MainLayout';
import DemandSubmitPage from './features/demand/DemandSubmitPage';
import NegotiationPage from './features/negotiation/NegotiationPage';
import DashboardPage from './features/dashboard/DashboardPage';
// Modern design pages
import SubmitDemand from './pages/SubmitDemand';
import Negotiation from './pages/Negotiation';

// Design System Token Configuration
// Aligned with CSS variables in index.css
const designTokens = {
  // Primary colors - Purple/Indigo gradient palette
  colorPrimary: '#6366f1',
  colorPrimaryHover: '#4f46e5',
  colorPrimaryActive: '#4338ca',
  colorPrimaryBg: 'rgba(99, 102, 241, 0.1)',
  colorPrimaryBgHover: 'rgba(99, 102, 241, 0.15)',

  // Semantic colors
  colorSuccess: '#22c55e',
  colorWarning: '#f59e0b',
  colorError: '#ef4444',
  colorInfo: '#3b82f6',

  // Background colors
  colorBgContainer: '#ffffff',
  colorBgElevated: '#ffffff',
  colorBgLayout: '#fafafa',
  colorBgSpotlight: '#f5f5f5',

  // Border colors
  colorBorder: '#e5e5e5',
  colorBorderSecondary: '#f0f0f0',

  // Text colors
  colorText: '#171717',
  colorTextSecondary: '#525252',
  colorTextTertiary: '#737373',
  colorTextQuaternary: '#a3a3a3',

  // Border radius - Modern rounded corners
  borderRadius: 8,
  borderRadiusSM: 6,
  borderRadiusLG: 12,
  borderRadiusXS: 4,

  // Typography - Using system font stack
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  fontFamilyCode: "'JetBrains Mono', 'Fira Code', 'SF Mono', Monaco, Consolas, monospace",

  // Shadows - Soft, modern shadows
  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
  boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',

  // Animation
  motionDurationFast: '150ms',
  motionDurationMid: '200ms',
  motionDurationSlow: '300ms',
  motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',

  // Sizing
  controlHeight: 36,
  controlHeightLG: 44,
  controlHeightSM: 28,
};

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: designTokens,
        components: {
          Button: {
            primaryShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.35)',
            defaultBorderColor: '#e5e5e5',
            defaultBg: '#ffffff',
            borderRadiusLG: 12,
          },
          Card: {
            borderRadiusLG: 16,
            boxShadowTertiary: '0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
          },
          Input: {
            activeBorderColor: '#6366f1',
            hoverBorderColor: '#a3a3a3',
            activeShadow: '0 0 0 3px rgba(99, 102, 241, 0.15)',
          },
          Select: {
            optionActiveBg: 'rgba(99, 102, 241, 0.1)',
            optionSelectedBg: 'rgba(99, 102, 241, 0.15)',
          },
          Table: {
            headerBg: '#fafafa',
            rowHoverBg: '#f5f5f5',
            borderColor: '#e5e5e5',
          },
          Modal: {
            borderRadiusLG: 16,
          },
          Menu: {
            itemSelectedBg: 'rgba(99, 102, 241, 0.1)',
            itemSelectedColor: '#6366f1',
            itemHoverBg: '#f5f5f5',
          },
          Tag: {
            borderRadiusSM: 9999, // Pills style
          },
          Badge: {
            dotSize: 8,
          },
          Message: {
            contentBg: '#ffffff',
            borderRadiusLG: 12,
          },
          Notification: {
            borderRadiusLG: 12,
          },
        },
      }}
    >
      <AntdApp>
        <BrowserRouter>
          <Routes>
            {/* Modern landing page - full screen gradient design */}
            <Route path="/" element={<SubmitDemand />} />
            <Route path="/negotiation/:demandId" element={<Negotiation />} />

            {/* Admin/Dashboard layout with sidebar */}
            <Route path="/admin" element={<MainLayout />}>
              <Route index element={<Navigate to="/admin/demand" replace />} />
              <Route path="demand" element={<DemandSubmitPage />} />
              <Route path="negotiations/:negotiationId" element={<NegotiationPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
