/**
 * Catch-all proxy for /store/api/* endpoints.
 *
 * The existence of app/store/api/assist-demand/route.ts causes Next.js
 * to "claim" the /store/api/ namespace, preventing rewrites from reaching
 * other backend endpoints (e.g. /store/api/history). This catch-all
 * proxies unmatched paths to the backend.
 *
 * More specific Route Handlers (like assist-demand) take precedence.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const subpath = path.join('/');
  const url = new URL(request.url);
  const qs = url.search; // preserve query string

  const upstream = await fetch(`${BACKEND_URL}/store/api/${subpath}${qs}`, {
    method: 'GET',
    headers: {
      Cookie: request.headers.get('cookie') || '',
    },
  });

  const body = await upstream.text();
  const responseHeaders: Record<string, string> = {
    'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
  };
  const setCookie = upstream.headers.get('Set-Cookie');
  if (setCookie) responseHeaders['Set-Cookie'] = setCookie;
  const cacheControl = upstream.headers.get('Cache-Control');
  if (cacheControl) responseHeaders['Cache-Control'] = cacheControl;

  return new Response(body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const subpath = path.join('/');

  const upstream = await fetch(`${BACKEND_URL}/store/api/${subpath}`, {
    method: 'POST',
    headers: {
      'Content-Type': request.headers.get('Content-Type') || 'application/json',
      Cookie: request.headers.get('cookie') || '',
    },
    body: await request.text(),
  });

  const body = await upstream.text();
  const responseHeaders: Record<string, string> = {
    'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
  };
  const setCookie = upstream.headers.get('Set-Cookie');
  if (setCookie) responseHeaders['Set-Cookie'] = setCookie;
  const cacheControl = upstream.headers.get('Cache-Control');
  if (cacheControl) responseHeaders['Cache-Control'] = cacheControl;

  return new Response(body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
