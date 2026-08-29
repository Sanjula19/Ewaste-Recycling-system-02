import React from 'react';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function LanguageSelector() {
  const { locale, setLocale, locales, t } = useLanguage();

  return (
    <label className="language-selector">
      <span className="sr-only">{t('language.select')}</span>
      <select value={locale} onChange={(e) => setLocale(e.target.value)}>
        {Object.entries(locales).map(([code, { label }]) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
