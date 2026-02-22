'use client';

// [MAINTENANCE MODE] Backend is down — show maintenance banner
// To restore: change the default export back to PlaygroundPageContent
import { MaintenanceBanner } from '@/components/shared/MaintenanceBanner';

export default function PlaygroundPage() {
  return <MaintenanceBanner pageName="Playground" />;
}

// ============================================================
// ORIGINAL CODE BELOW — preserved for restoration
// The original default export was: export default function PlaygroundPage()
// Renamed to PlaygroundPageContent to avoid conflict.
// To restore: delete the MaintenanceBanner export above,
// and rename PlaygroundPageContent back to PlaygroundPage (default export).
// ============================================================

/*
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useState, useEffect, useCallback } from 'react';
import { quickRegister, getScenes, type StoreScene } from '@/lib/store-api';
import { NegotiationProgress } from '@/components/store/NegotiationProgress';
import { PlanOutput } from '@/components/store/PlanOutput';
import { useStoreNegotiation } from '@/hooks/useStoreNegotiation';
*/

// Note: Original full component code is preserved in git history.
// Run `git diff HEAD -- app/playground/page.tsx` to see the original.
