/**
 * Catch-all proxy for /store/api/* endpoints.
 *
 * [MAINTENANCE MODE] Backend is down — return 503 Service Unavailable.
 * To restore: replace this file content with the original from git history.
 * Run: git checkout HEAD -- "app/store/api/[...path]/route.ts"
 */

const MAINTENANCE_RESPONSE = JSON.stringify({
  error: 'Service temporarily unavailable',
  message: '服务器正在维护中，请稍后再试',
});

const MAINTENANCE_HEADERS = {
  'Content-Type': 'application/json',
  'Retry-After': '3600',
};

export async function GET() {
  return new Response(MAINTENANCE_RESPONSE, {
    status: 503,
    headers: MAINTENANCE_HEADERS,
  });
}

export async function POST() {
  return new Response(MAINTENANCE_RESPONSE, {
    status: 503,
    headers: MAINTENANCE_HEADERS,
  });
}

// Original proxy code preserved in git history.
