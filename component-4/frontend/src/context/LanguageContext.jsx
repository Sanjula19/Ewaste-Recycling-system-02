import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { LOCALES, DEFAULT_LOCALE, translate } from '../i18n/index.js';

const LanguageContext = createContext(null);
const STORAGE_KEY = 'ecovision.locale';

export function LanguageProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved && LOCALES[saved] ? saved : DEFAULT_LOCALE;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next) => {
    if (LOCALES[next]) setLocaleState(next);
  }, []);

  const t = useCallback(
    (path) => translate(LOCALES[locale].dict, path),
    [locale]
  );

  const value = {
    locale,
    setLocale,
    t,
    intlTag: LOCALES[locale].intl,
    locales: LOCALES,
  };

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within a LanguageProvider');
  return ctx;
}
