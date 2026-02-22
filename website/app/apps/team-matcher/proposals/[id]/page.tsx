// [MAINTENANCE MODE] Backend is down — show maintenance banner
// Original code: import { ProposalsPageClient } from './ProposalsPageClient';
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Team Matcher - 团队方案 | ToWow',
  description: '查看 AI 生成的多种团队组合方案',
};

export default function ProposalsPage() {
  // const { id } = await params;
  // return <ProposalsPageClient requestId={id} />;
  return <MaintenanceBanner pageName="Team Matcher" />;
}
