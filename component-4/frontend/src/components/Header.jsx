import React from 'react';
import { Menu, Leaf } from 'lucide-react';
import LiveClock from './LiveClock.jsx';
import LanguageSelector from './LanguageSelector.jsx';
import ThemeToggle from './ThemeToggle.jsx';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function Header({ onMenuClick }) {
  const { t } = useLanguage();

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          type="button"
          className="menu-toggle"
          onClick={onMenuClick}
          aria-label="Toggle navigation"
        >
          <Menu size={20} />
        </button>
        <div className="brand">
          <span className="brand-icon">
            <Leaf size={20} />
          </span>
          <div className="brand-text">
            <span className="brand-name">{t('app.name')}</span>
            <span className="brand-tagline">{t('app.tagline')}</span>
          </div>
        </div>
      </div>

      <div className="header-right">
        <LiveClock />
        <LanguageSelector />
        <ThemeToggle />
      </div>
    </header>
  );
}
