import { Metadata } from 'next';
import { ProposalsPageClient } from './ProposalsPageClient';

export const metadata: Metadata = {
  title: 'Team Matcher - 团队方案 | ToWow',
  description: '查看 AI 生成的多种团队组合方案',
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProposalsPage({ params }: PageProps) {
  const { id } = await params;
  return <ProposalsPageClient requestId={id} />;
}
