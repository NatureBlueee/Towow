import type { Metadata } from 'next';
import { NegotiationPage } from '@/components/negotiation/NegotiationPage';

export const metadata: Metadata = {
  title: 'Negotiation - ToWow',
  description: 'Start a negotiation to find the right collaborators through AI agent resonance',
};

export default function Page() {
  return <NegotiationPage />;
}
