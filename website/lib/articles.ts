// lib/articles.ts
// Re-export from the new locale-aware module for backwards compatibility.
// New code should import from '@/lib/articles/index' directly.

export { getArticles, getArticleBySlug, getAllArticleSlugs } from './articles/index';
export type { Article, ArticleSection } from './articles/types';

// Legacy: export zhArticles as 'articles' for any code still using the named import
import { zhArticles } from './articles/zh';
export const articles = zhArticles;
