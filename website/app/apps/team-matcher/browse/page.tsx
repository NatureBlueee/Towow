import { Metadata } from 'next';
import { BrowsePageClient } from './BrowsePageClient';

export const metadata: Metadata = {
  title: 'Team Matcher - 浏览请求 | ToWow',
  description: '浏览开放的组队请求，响应感兴趣的项目',
};

export default function BrowsePage() {
  return <BrowsePageClient />;
}
