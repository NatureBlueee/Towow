export interface Stat {
  num: string;
  label: string;
}

export interface Transformation {
  label: string;
  time: string;
  oneLiner: string;
  meaning: string;
}

export interface Phase {
  num: number;
  name: string;
  dates: string;
  narrative: string;
  decisions: string[];
  corrections: string[];
  surprise: string;
  quote: string;
  quoteAuthor?: string;
  tags: { label: string; color: 'code' | 'design' | 'doc' | 'deploy' }[];
  stats: string;
}

export interface Compact {
  num: number;
  date: string;
  title: string;
  detail: string;
}

export interface Session {
  label: string;
  dateRange: string;
  color: string;
  compacts: Compact[];
}

export interface JourneyData {
  stats: Stat[];
  transformations: Transformation[];
  phases: Phase[];
  sessions: Session[];
}
