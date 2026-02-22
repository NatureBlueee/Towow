'use client';

// [MAINTENANCE MODE] Backend is down — show maintenance banner
// To restore: replace this file content with the original from git history
// Run: git checkout HEAD -- app/enter/page.tsx
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

export default function EnterPage() {
  return <MaintenanceBanner pageName="加入网络" />;
}

// Original code preserved in git history.
// Run `git diff HEAD -- app/enter/page.tsx` to see what was changed.
