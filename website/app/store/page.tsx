'use client';

// [MAINTENANCE MODE] Backend is down — show maintenance banner
// To restore: replace this file content with the original from git history
// Run: git checkout HEAD -- app/store/page.tsx
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

export default function StorePage() {
  return <MaintenanceBanner pageName="App Store" />;
}

// Original code preserved in git history.
// Run `git diff HEAD -- app/store/page.tsx` to see what was changed.
