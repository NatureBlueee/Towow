import { Metadata } from 'next';
import { RespondPageClient } from './RespondPageClient';

export const metadata: Metadata = {
  title: 'Team Matcher - 响应组队 | ToWow',
  description: '查看组队请求详情并提交你的参与意向',
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function RespondPage({ params }: PageProps) {
  const { id } = await params;
  return <RespondPageClient requestId={id} />;
}
