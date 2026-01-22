import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器 - 添加认证 token（如果有）
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 清除本地存储的认证信息
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_info');

      // 如果不在登录页，重定向到首页
      if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
        console.warn('Session expired, redirecting to home page');
        window.location.href = '/';
      }
    }

    // 统一错误格式
    const errorMessage = error.response?.data?.detail
      || error.response?.data?.message
      || error.message
      || '请求失败';

    return Promise.reject(new Error(errorMessage));
  }
);

export const createSSEConnection = (endpoint: string): EventSource => {
  return new EventSource(`${API_BASE}${endpoint}`);
};
