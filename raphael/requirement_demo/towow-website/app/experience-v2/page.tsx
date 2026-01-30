import { Metadata } from 'next';
import { Suspense } from 'react';
import { ExperienceProvider } from '@/context/ExperienceContext';
import { ExperienceV2PageClient } from './ExperienceV2PageClient';
import { LoadingScreen } from '@/components/experience/LoadingScreen';

export const metadata: Metadata = {
  title: 'ToWow Experience V2 - AI Agent 协作演示',
  description: '体验 AI Agent 协作网络的全新交互流程',
};

export default function ExperienceV2Route() {
  return (
    <ExperienceProvider>
      <Suspense fallback={<LoadingScreen message="加载中..." />}>
        <ExperienceV2PageClient />
      </Suspense>
    </ExperienceProvider>
  );
}
