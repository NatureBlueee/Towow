// [MAINTENANCE MODE] Backend is down — show maintenance banner
// Original code: import { ProgressPageClient } from './ProgressPageClient';
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Team Matcher - 等待共振 | ToWow',
  description: '你的信号正在广播，等待伙伴响应',
};

export default function ProgressPage() {
  // const { id } = await params;
  // return <ProgressPageClient requestId={id} />;
  return <MaintenanceBanner pageName="Team Matcher" />;
}
