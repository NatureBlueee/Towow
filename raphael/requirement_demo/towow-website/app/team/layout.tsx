import { ReactNode } from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Team Matcher - ToWow',
  description: '发出信号，找到共振的伙伴，组建最佳团队',
};

export default function TeamLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
