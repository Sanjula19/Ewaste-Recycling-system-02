import React from 'react';
import { COMPONENTS, GATEWAY_URL } from '../config.js';
import { useGatewayHealth } from '../useGatewayHealth.js';
import ComponentCard from '../components/ComponentCard.jsx';

export default function Home() {
  const health = useGatewayHealth();

  return (
    <div>
      <h1>System Overview</h1>
      <p className="page-subtitle">
        Unified navigation shell for the four independent components. Each card links to that
        component's own existing frontend — nothing is merged.
      </p>

      {!health.loading && !health.gatewayReachable && (
        <div className="warning-banner">
          API Gateway unreachable at <code>{GATEWAY_URL}</code>. Component status shows as
          Unknown until the gateway ({GATEWAY_URL}) is running.
        </div>
      )}

      <div className="card-grid">
        {COMPONENTS.map((c) => (
          <ComponentCard
            key={c.id}
            component={c}
            status={health.gatewayReachable ? health.services[c.key]?.status : 'unknown'}
          />
        ))}
      </div>
    </div>
  );
}
