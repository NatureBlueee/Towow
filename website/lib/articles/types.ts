// lib/articles/types.ts

export interface ArticleSection {
  id: string;
  title: string;
  content: string;
}

export interface Article {
  slug: string;
  title: string;
  readingTime: number;
  date: string;
  heroImages?: {
    right?: string;
    left?: string;
  };
  sections: ArticleSection[];
  relatedArticles: {
    slug: string;
    title: string;
    icon: 'handshake' | 'globe' | 'user' | 'lightbulb' | 'book';
  }[];
}
