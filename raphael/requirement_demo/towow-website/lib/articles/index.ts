// lib/articles/index.ts
// Locale-aware article data selector

import { zhArticles } from './zh';
import { enArticles } from './en';
import type { Article, ArticleSection } from './types';

export function getArticles(locale: string): Article[] {
  return locale === 'en' ? enArticles : zhArticles;
}

export function getArticleBySlug(slug: string, locale: string = 'zh'): Article | undefined {
  const articles = getArticles(locale);
  return articles.find((a) => a.slug === slug);
}

export function getAllArticleSlugs(): string[] {
  // Slugs are the same across locales
  return zhArticles.map((a) => a.slug);
}

// Re-export zhArticles as default "articles" for backward compatibility
export const articles = zhArticles;

export type { Article, ArticleSection };
