import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

export const formatCurrency = (
  amount: number,
  currency = 'CNY',
  locale = 'zh-CN'
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(amount);
};

export const formatDateTime = (date: string | Date): string => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
};

export const formatRelativeTime = (date: string | Date): string => {
  return dayjs(date).fromNow();
};

export const formatDate = (date: string | Date): string => {
  return dayjs(date).format('YYYY-MM-DD');
};

export const formatTime = (date: string | Date): string => {
  return dayjs(date).format('HH:mm');
};

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
};

export const capitalizeFirst = (str: string): string => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
};

export const statusColorMap: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  awaiting_user: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
};

export const getStatusColor = (status: string): string => {
  return statusColorMap[status] || 'default';
};
