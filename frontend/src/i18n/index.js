import en from './en.js';
import si from './si.js';
import ta from './ta.js';

export const LOCALES = {
  en: { label: 'English', dict: en, intl: 'en-US' },
  si: { label: 'සිංහල', dict: si, intl: 'si-LK' },
  ta: { label: 'தமிழ்', dict: ta, intl: 'ta-LK' },
};

export const DEFAULT_LOCALE = 'en';

/** Looks up a dot-path like "forecast.sellNow" in one dictionary. */
function lookup(dict, path) {
  const parts = path.split('.');
  let node = dict;
  for (const part of parts) {
    if (node == null) return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

/*
  Looks up a dot-path, falling back to English when the active locale has
  no entry for it.

  This used to return the raw path, so an untranslated key rendered in the
  UI as literally "disposition.recommended" -- worse than showing English,
  and it made adding a label a breaking change for si/ta until someone
  translated it. Now a new key is immediately usable in every locale and
  can be translated later. The path is still the last resort, so a genuine
  typo in a key name stays visible rather than silently rendering blank.
*/
export function translate(dict, path) {
  return lookup(dict, path) ?? lookup(en, path) ?? path;
}
