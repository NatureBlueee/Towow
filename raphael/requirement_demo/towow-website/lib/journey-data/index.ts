import { zhData } from './zh';
import { enData } from './en';
import type { JourneyData } from './types';

export type { Stat, Transformation, Phase, Compact, Session, JourneyData } from './types';

export function getJourneyData(locale: string): JourneyData {
  return locale === 'en' ? enData : zhData;
}
