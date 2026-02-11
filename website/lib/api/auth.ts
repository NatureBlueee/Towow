// 使用相对路径，通过 Next.js rewrites 代理到后端

/**
 * 构建 SecondMe OAuth2 登录 URL。
 * 后端 GET /api/auth/secondme/start 返回 302 重定向，
 * 所以直接构造 URL 让浏览器导航过去。
 */
export function getAuthUrl(returnTo?: string): string {
  const params = returnTo ? `?return_to=${encodeURIComponent(returnTo)}` : '';
  return `/api/auth/secondme/start${params}`;
}

export async function getCurrentUser() {
  const response = await fetch('/api/auth/me', {
    credentials: 'include',
  });
  if (!response.ok) return null;
  return response.json();
}

export async function logout() {
  await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include',
  });
}
