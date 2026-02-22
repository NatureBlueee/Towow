// [MAINTENANCE MODE] Backend is down — show maintenance banner
// Original code: import { RespondPageClient } from './RespondPageClient';
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Team Matcher - 响应组队 | ToWow',
  description: '查看组队请求详情并提交你的参与意向',
};

export default function RespondPage() {
  // const { id } = await params;
  // return <RespondPageClient requestId={id} />;
  return <MaintenanceBanner pageName="Team Matcher" />;
}
