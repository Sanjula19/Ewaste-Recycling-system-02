import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Recycle, FileText } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, i18nKey: 'nav.dashboard', end: true },
  { to: '/forecast', icon: TrendingUp, i18nKey: 'nav.forecast' },
  { to: '/disposition', icon: Recycle, i18nKey: 'nav.disposition' },
  { to: '/manifest', icon: FileText, i18nKey: 'nav.manifest' },
];

export default function Sidebar({ open, onNavigate }) {
  const { t } = useLanguage();

  return (
    <nav className={`app-sidebar ${open ? 'open' : ''}`} aria-label="Primary">
      {NAV_ITEMS.map(({ to, icon: Icon, i18nKey, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
        >
          <Icon size={18} />
          <span>{t(i18nKey)}</span>
        </NavLink>
      ))}
    </nav>
  );
}
