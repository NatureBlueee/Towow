import { Metadata } from 'next';
import { TeamRequestPageClient } from './TeamRequestPageClient';

export const metadata: Metadata = {
  title: 'Team Matcher - 发出信号 | ToWow',
  description: '描述你的项目想法，让共振帮你找到最佳伙伴',
};

export default function TeamRequestPage() {
  return <TeamRequestPageClient />;
}
