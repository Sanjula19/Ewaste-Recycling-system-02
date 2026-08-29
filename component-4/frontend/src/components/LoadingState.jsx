import React from 'react';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function LoadingState() {
  const { t } = useLanguage();
  return (
    <div className="loading-state">
      <div className="spinner" />
      <span>{t('common.loading')}</span>
    </div>
  );
}
