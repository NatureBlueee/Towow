import { Metadata } from 'next';
import { ProgressPageClient } from './ProgressPageClient';

export const metadata: Metadata = {
  title: 'Team Matcher - 等待共振 | ToWow',
  description: '你的信号正在广播，等待伙伴响应',
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProgressPage({ params }: PageProps) {
  const { id } = await params;
  return <ProgressPageClient requestId={id} />;
}
