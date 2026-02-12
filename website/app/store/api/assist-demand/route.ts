/**
 * SSE proxy for assist-demand.
 *
 * Next.js rewrites buffer SSE responses, so we proxy through a
 * Route Handler that streams the backend response directly.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function POST(request: Request) {
  const body = await request.text();

  // Forward cookies for SecondMe auth
  const cookie = request.headers.get('cookie') || '';

  const upstream = await fetch(`${BACKEND_URL}/store/api/assist-demand`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Cookie: cookie,
    },
    body,
    cache: 'no-cache',
  });

  if (!upstream.ok) {
    const text = await upstream.text().catch(() => '');
    return new Response(text || upstream.statusText, { status: upstream.status });
  }

  // Stream the SSE body directly — no buffering
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-store',
      'X-Accel-Buffering': 'no',
    },
  });
}
