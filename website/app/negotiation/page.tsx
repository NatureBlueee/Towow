// [MAINTENANCE MODE] Backend is down — show maintenance banner
// Original code: import { NegotiationPage } from '@/components/negotiation/NegotiationPage';
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Negotiation - ToWow',
  description: 'Start a negotiation to find the right collaborators through AI agent resonance',
};

export default function Page() {
  // return <NegotiationPage />;
  return <MaintenanceBanner pageName="Negotiation" />;
}
