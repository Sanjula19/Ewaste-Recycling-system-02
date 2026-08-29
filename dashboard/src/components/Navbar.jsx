import React from 'react';
import { NavLink } from 'react-router-dom';
import { BRAND, STAGES } from '../config.js';
import { useTheme } from '../useTheme.js';
import { useGatewayHealth } from '../useGatewayHealth.js';

const NAV_LINKS = [
  { to: '/', label: 'Overview', end: true },
  ...STAGES.map((s) => ({ to: s.path, label: s.label })),
  { to: '/history', label: 'History' },
];

const STATUS_LABEL = {
  ok: 'All systems online',
  degraded: 'Degraded',
  unreachable: 'Gateway unreachable',
  unknown: 'Checking…',
};

export default function Navbar() {
  const { theme, toggle } = useTheme();
  const health = useGatewayHealth();
  const overall = health.loading ? 'unknown' : health.overallStatus;

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand">
          <span className="brand-mark">♻</span>
          <span className="brand-name mono">{BRAND}</span>
        </div>

        <nav className="nav-links">
          {NAV_LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="navbar-right">
          <span className={`status-pill status-${overall}`}>
            <span className="dot" />
            <span className="mono">{STATUS_LABEL[overall] || 'Unknown'}</span>
          </span>
          <button className="theme-toggle" onClick={toggle} title="Toggle theme">
            {theme === 'dark' ? '☀' : '🌙'}
          </button>
        </div>
      </div>
    </header>
  );
}
