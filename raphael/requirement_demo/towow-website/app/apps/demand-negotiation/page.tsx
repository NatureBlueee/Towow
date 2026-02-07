import { Metadata } from 'next';
import { Suspense } from 'react';
import { ExperienceProvider } from '@/context/ExperienceContext';
import { ExperienceV2PageClient } from './ExperienceV2PageClient';
import { LoadingScreen } from '@/components/shared/LoadingScreen';

export const metadata: Metadata = {
  title: 'ToWow 需求协商 - AI Agent 协作演示',
  description: '多 Agent 需求协商演示 - 体验 AI Agent 如何协作',
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
