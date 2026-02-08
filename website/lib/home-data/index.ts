// lib/home-data/index.ts
import { zhSections, zhNodes } from './zh';
import { enSections, enNodes } from './en';

export function getHomeSections(locale: string) {
  return locale === 'en' ? enSections : zhSections;
}

export function getNetworkNodes(locale: string) {
  return locale === 'en' ? enNodes : zhNodes;
}
