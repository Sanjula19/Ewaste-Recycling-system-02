import React from 'react';
import { NavLink } from 'react-router-dom';
import { COMPONENTS } from '../config.js';
import { useGatewayHealth } from '../useGatewayHealth.js';

export default function Sidebar() {
  const health = useGatewayHealth();

  function statusFor(key) {
    if (!health.gatewayReachable) return 'unknown';
    return health.services[key]?.status || 'unknown';
  }

  return (
    <aside className="sidebar">
      <nav>
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active' : '')}>
          System Overview
        </NavLink>
        {COMPONENTS.map((c) => (
          <NavLink
            key={c.id}
            to={c.path}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            <span className={`dot ${statusFor(c.key)}`} />
            {c.name.replace(/^Component \d+ — /, '')}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
