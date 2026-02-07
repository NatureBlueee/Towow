import { Metadata } from 'next';
import { Suspense } from 'react';
import { ExperienceProvider } from '@/context/ExperienceContext';
import { ExperienceV3PageClient } from './ExperienceV3PageClient';
import { LoadingScreen } from '@/components/experience/LoadingScreen';

export const metadata: Metadata = {
  title: 'ToWow Experience V3 - AI Agent 协作业务版',
  description: '体验 AI Agent 协作网络的真实业务流程',
};

export default function ExperienceV3Route() {
  return (
    <ExperienceProvider>
      <Suspense fallback={<LoadingScreen message="加载中..." />}>
        <ExperienceV3PageClient />
      </Suspense>
    </ExperienceProvider>
  );
}
