import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'App Store - 通爻网络',
  description: 'AI Agent 协作网络 — 发现、协商、协作',
};

export default function StoreLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
