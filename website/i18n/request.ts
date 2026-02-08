import {getRequestConfig} from 'next-intl/server';
import {cookies} from 'next/headers';

const SUPPORTED_LOCALES = ['zh', 'en'] as const;
const DEFAULT_LOCALE = 'zh';

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get('locale')?.value;
  const locale = raw && (SUPPORTED_LOCALES as readonly string[]).includes(raw)
    ? raw
    : DEFAULT_LOCALE;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
