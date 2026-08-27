import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function ErrorState({ message, onRetry }) {
  const { t } = useLanguage();
  return (
    <div className="alert alert-danger" role="alert">
      <AlertTriangle size={20} />
      <div style={{ flex: 1 }}>
        <p>{message || t('common.error')}</p>
        {onRetry && (
          <button type="button" className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onRetry}>
            {t('common.retry')}
          </button>
        )}
      </div>
    </div>
  );
}
