/**
 * 统一错误处理工具
 * 提供 API 错误处理、HTTP 错误消息、网络错误检测等功能
 */

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * HTTP 状态码对应的中文错误消息
 */
const HTTP_ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误，请检查输入内容',
  401: '登录已过期，请重新登录',
  403: '您没有权限执行此操作',
  404: '请求的资源不存在',
  408: '请求超时，请稍后重试',
  409: '操作冲突，请刷新后重试',
  422: '提交的数据格式不正确',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误，请稍后重试',
  502: '网关错误，服务暂时不可用',
  503: '服务暂时不可用，请稍后重试',
  504: '网关超时，请稍后重试',
};

/**
 * 错误代码对应的中文消息
 */
const ERROR_CODE_MESSAGES: Record<string, string> = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  TIMEOUT: '请求超时，请稍后重试',
  PARSE_ERROR: '数据解析失败',
  UNKNOWN: '发生未知错误，请稍后重试',
  AUTH_FAILED: '认证失败，请重新登录',
  OAUTH_CALLBACK_ERROR: 'OAuth2 授权回调失败',
  WEBSOCKET_ERROR: 'WebSocket 连接错误',
  WEBSOCKET_CLOSED: 'WebSocket 连接已断开',
  NEGOTIATION_TIMEOUT: '协商超时，请重新提交需求',
  VALIDATION_ERROR: '输入验证失败，请检查填写内容',
};

/**
 * 处理 API 错误，返回统一格式的错误对象
 */
export function handleApiError(error: unknown): ApiError {
  // 处理 Response 对象
  if (error instanceof Response) {
    return {
      code: `HTTP_${error.status}`,
      message: getHttpErrorMessage(error.status),
      details: { status: error.status, statusText: error.statusText },
    };
  }

  // 处理网络错误
  if (isNetworkError(error)) {
    return {
      code: 'NETWORK_ERROR',
      message: ERROR_CODE_MESSAGES.NETWORK_ERROR,
      details: { originalError: String(error) },
    };
  }

  // 处理超时错误
  if (isTimeoutError(error)) {
    return {
      code: 'TIMEOUT',
      message: ERROR_CODE_MESSAGES.TIMEOUT,
    };
  }

  // 处理已格式化的 ApiError
  if (isApiError(error)) {
    return {
      code: error.code,
      message: ERROR_CODE_MESSAGES[error.code] || error.message,
      details: error.details,
    };
  }

  // 处理标准 Error 对象
  if (error instanceof Error) {
    // 检查是否是 fetch 的 AbortError
    if (error.name === 'AbortError') {
      return {
        code: 'TIMEOUT',
        message: ERROR_CODE_MESSAGES.TIMEOUT,
      };
    }

    return {
      code: 'UNKNOWN',
      message: error.message || ERROR_CODE_MESSAGES.UNKNOWN,
      details: { name: error.name, stack: error.stack },
    };
  }

  // 处理字符串错误
  if (typeof error === 'string') {
    return {
      code: 'UNKNOWN',
      message: error,
    };
  }

  // 处理包含 message 字段的对象
  if (error && typeof error === 'object' && 'message' in error) {
    const errObj = error as { message: string; code?: string; details?: Record<string, unknown> };
    return {
      code: errObj.code || 'UNKNOWN',
      message: errObj.message,
      details: errObj.details,
    };
  }

  // 默认未知错误
  return {
    code: 'UNKNOWN',
    message: ERROR_CODE_MESSAGES.UNKNOWN,
    details: { originalError: String(error) },
  };
}

/**
 * 根据 HTTP 状态码获取用户友好的错误消息
 */
export function getHttpErrorMessage(status: number): string {
  return HTTP_ERROR_MESSAGES[status] || `请求失败 (错误码: ${status})`;
}

/**
 * 检测是否为网络错误
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError) {
    const message = error.message.toLowerCase();
    return (
      message.includes('network') ||
      message.includes('fetch') ||
      message.includes('failed to fetch') ||
      message.includes('networkerror') ||
      message.includes('network request failed')
    );
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    return (
      message.includes('network') ||
      message.includes('econnrefused') ||
      message.includes('enotfound') ||
      message.includes('etimedout')
    );
  }

  return false;
}

/**
 * 检测是否为超时错误
 */
export function isTimeoutError(error: unknown): boolean {
  if (error instanceof Error) {
    return (
      error.name === 'AbortError' ||
      error.name === 'TimeoutError' ||
      error.message.toLowerCase().includes('timeout')
    );
  }
  return false;
}

/**
 * 类型守卫：检查是否为 ApiError 类型
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'code' in error &&
    'message' in error &&
    typeof (error as ApiError).code === 'string' &&
    typeof (error as ApiError).message === 'string'
  );
}

/**
 * 创建自定义 API 错误
 */
export function createApiError(
  code: string,
  message?: string,
  details?: Record<string, unknown>
): ApiError {
  return {
    code,
    message: message || ERROR_CODE_MESSAGES[code] || ERROR_CODE_MESSAGES.UNKNOWN,
    details,
  };
}

/**
 * 获取错误代码对应的消息
 */
export function getErrorMessage(code: string): string {
  return ERROR_CODE_MESSAGES[code] || ERROR_CODE_MESSAGES.UNKNOWN;
}

/**
 * WebSocket 连接状态相关错误
 */
export const WebSocketErrors = {
  CONNECTING: createApiError('WEBSOCKET_CONNECTING', '正在连接服务器...'),
  DISCONNECTED: createApiError('WEBSOCKET_CLOSED', 'WebSocket 连接已断开，正在尝试重连...'),
  ERROR: createApiError('WEBSOCKET_ERROR', 'WebSocket 连接错误'),
  MAX_RETRIES: createApiError('WEBSOCKET_MAX_RETRIES', '连接失败次数过多，请刷新页面重试'),
} as const;

/**
 * OAuth2 相关错误
 */
export const OAuth2Errors = {
  CALLBACK_FAILED: createApiError('OAUTH_CALLBACK_ERROR', 'OAuth2 授权回调失败，请重新登录'),
  TOKEN_EXPIRED: createApiError('AUTH_FAILED', '登录已过期，请重新登录'),
  ACCESS_DENIED: createApiError('AUTH_FAILED', '授权被拒绝，请重新尝试'),
} as const;

/**
 * 协商相关错误
 */
export const NegotiationErrors = {
  TIMEOUT: createApiError('NEGOTIATION_TIMEOUT', '协商超时，请重新提交需求'),
  FAILED: createApiError('NEGOTIATION_FAILED', '协商失败，请稍后重试'),
  NO_PARTICIPANTS: createApiError('NO_PARTICIPANTS', '没有可用的参与者'),
} as const;
