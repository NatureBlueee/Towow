/**
 * SSE proxy for assist-demand.
 *
 * [MAINTENANCE MODE] Backend is down — return 503 Service Unavailable.
 * To restore: replace this file content with the original from git history.
 * Run: git checkout HEAD -- "app/store/api/assist-demand/route.ts"
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function POST() {
  return new Response(
    JSON.stringify({
      error: 'Service temporarily unavailable',
      message: '服务器正在维护中，请稍后再试',
    }),
    {
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'Retry-After': '3600',
      },
    },
  );
}

// Original SSE proxy code preserved in git history.
