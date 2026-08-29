import React from 'react';
import StatusBadge from '../components/StatusBadge.jsx';
import { useGatewayHealth } from '../useGatewayHealth.js';

// Generic detail/launcher page shared by all four component routes.
// This is a shell page ONLY — it never embeds or reimplements the
// component's own UI. Opening the component always happens in a new tab,
// so the component's existing frontend runs completely on its own.
export default function ComponentDetail({ component }) {
  const health = useGatewayHealth();
  const status = health.gatewayReachable ? health.services[component.key]?.status : 'unknown';
  const detail = health.gatewayReachable ? health.services[component.key]?.detail : null;

  return (
    <div>
      <h1>{component.name}</h1>
      <h2>Owner: {component.owner}</h2>

      {component.key === 'component2' && (
        <div className="independent-banner">
          Component 2 is a completely independent service. It is not called by, and does not
          call, Component 1, 3, or 4 — this page only links to its existing dashboard.
        </div>
      )}

      {component.limitation && (
        <div className="warning-banner">{component.limitation}</div>
      )}

      <div className="detail-section">
        <p className="card-desc">{component.description}</p>
        <p className="workflow-tag">Workflow: {component.workflow}</p>
      </div>

      <div className="detail-section">
        <div className="card-title-row" style={{ marginBottom: 12 }}>
          <span className="card-title">Backend status (via API Gateway)</span>
          <StatusBadge status={status} />
        </div>
        {status === 'unavailable' && (
          <p className="card-desc">
            Service unavailable — the backend for this component is not currently reachable.
            {detail ? ` (${detail})` : ''}
          </p>
        )}
        {!component.hasFrontend && (
          <p className="card-desc">
            This component has no web frontend. Data acquisition happens on a Raspberry Pi
            (camera + load cell). The link below opens the backend API directly.
          </p>
        )}
      </div>

      <a className="btn btn-primary" href={component.openUrl} target="_blank" rel="noreferrer">
        {component.openLabel}
      </a>
    </div>
  );
}
