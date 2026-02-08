import type { Metadata } from 'next';
import { NegotiatePage } from './NegotiatePageClient';

export const metadata: Metadata = {
  title: 'Negotiate - ToWow',
  description: 'Start a negotiation to find the right collaborators',
};

export default function Page() {
  return <NegotiatePage />;
}
