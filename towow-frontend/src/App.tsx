import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/layout/MainLayout';
import DemandSubmitPage from './features/demand/DemandSubmitPage';
import NegotiationPage from './features/negotiation/NegotiationPage';
import DashboardPage from './features/dashboard/DashboardPage';

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/demand" replace />} />
              <Route path="demand" element={<DemandSubmitPage />} />
              <Route path="negotiations/:negotiationId" element={<NegotiationPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
