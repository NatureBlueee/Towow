import { Metadata } from 'next';
import { ExperienceV2Page } from '@/components/experience-v2';

export const metadata: Metadata = {
  title: 'ToWow Experience V2 - AI Agent 协作演示',
  description: '体验 AI Agent 协作网络的全新交互流程',
};

export default function ExperienceV2Route() {
  return <ExperienceV2Page />;
}
