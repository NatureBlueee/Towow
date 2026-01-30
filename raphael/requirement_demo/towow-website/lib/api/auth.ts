const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function getAuthUrl(): Promise<string> {
  const response = await fetch(`${API_BASE}/api/auth/login`);
  const data = await response.json();
  // 后端返回的是 authorization_url
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
