import React from 'react';
import { WifiOff } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function ConnectionBanner() {
  const { t } = useLanguage();
  return (
    <div className="alert alert-danger" role="alert">
      <WifiOff size={20} />
      <div>
        <p style={{ fontWeight: 700 }}>{t('common.connectionError')}</p>
        <p>{t('common.connectionErrorHint')}</p>
      </div>
    </div>
  );
}
