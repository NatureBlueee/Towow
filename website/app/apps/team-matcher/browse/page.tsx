// [MAINTENANCE MODE] Backend is down — show maintenance banner
// Original code: import { BrowsePageClient } from './BrowsePageClient';
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Team Matcher - 浏览请求 | ToWow',
  description: '浏览开放的组队请求，响应感兴趣的项目',
};

export default function BrowsePage() {
  // return <BrowsePageClient />;
  return <MaintenanceBanner pageName="Team Matcher" />;
}
