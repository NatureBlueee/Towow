// 使用相对路径，通过 Next.js rewrites 代理到后端
const API_BASE = '';

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
