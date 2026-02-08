import { zhTracks } from './zh';
import { enTracks } from './en';
import type { Track } from './types';

export type { Track, Task } from './types';

export function getContributeData(locale: string): Track[] {
  return locale === 'en' ? enTracks : zhTracks;
}
