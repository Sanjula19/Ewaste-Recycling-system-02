import en from './en.js';
import si from './si.js';
import ta from './ta.js';

export const LOCALES = {
  en: { label: 'English', dict: en, intl: 'en-US' },
  si: { label: 'සිංහල', dict: si, intl: 'si-LK' },
  ta: { label: 'தமிழ்', dict: ta, intl: 'ta-LK' },
};

export const DEFAULT_LOCALE = 'en';

/** Looks up a dot-path like "forecast.sellNow" in a locale dictionary. */
export function translate(dict, path) {
  const parts = path.split('.');
  let node = dict;
  for (const part of parts) {
    if (node == null) return path;
    node = node[part];
  }
  return typeof node === 'string' ? node : path;
}
