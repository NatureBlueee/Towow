import { Suspense } from 'react';
import { ExperienceProvider } from '@/context/ExperienceContext';
import { ExperiencePageClient } from './ExperiencePageClient';
import { LoadingScreen } from '@/components/experience/LoadingScreen';

export const metadata = {
  title: 'ToWow Experience - Agent Collaboration Demo',
  description: 'Experience AI Agent Collaboration Network',
};

export default function ExperiencePage() {
  return (
    <ExperienceProvider>
      <Suspense fallback={<LoadingScreen message="加载中..." />}>
        <ExperiencePageClient />
      </Suspense>
    </ExperienceProvider>
  );
}
