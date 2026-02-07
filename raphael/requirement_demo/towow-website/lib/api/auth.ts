// 使用相对路径，通过 Next.js rewrites 代理到后端
const API_BASE = '';

export async function getAuthUrl(returnTo?: string): Promise<string> {
  const params = returnTo ? `?return_to=${encodeURIComponent(returnTo)}` : '';
  const response = await fetch(`${API_BASE}/api/auth/login${params}`);
  if (!response.ok) {
    throw new Error(`Auth API error: ${response.status}`);
  }
  const data = await response.json();
  if (!data.authorization_url) {
    throw new Error('No authorization_url in response');
  }
  return data.authorization_url;
}

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    credentials: 'include',
  });
  if (!response.ok) return null;
  return response.json();
}

export async function logout() {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
}
