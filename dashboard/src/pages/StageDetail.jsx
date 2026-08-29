import React from 'react';
import StatusBadge from '../components/StatusBadge.jsx';
import { useGatewayHealth } from '../useGatewayHealth.js';

// Generic launcher/info page shared by Detect/Protect/Process/Recover. This
// is a shell page ONLY — it never embeds or reimplements that section's own
// application. Opening it always happens in a new tab, so the underlying
// component's frontend runs completely on its own, untouched.
export default function StageDetail({ stage }) {
  const health = useGatewayHealth();
  const status = health.gatewayReachable ? health.services[stage.componentKey]?.status : 'unknown';
  const detail = health.gatewayReachable ? health.services[stage.componentKey]?.detail : null;

  return (
    <div>
      <h1 className="page-title">{stage.label}</h1>
      <p className="page-subtitle">{stage.tagline}</p>

      {stage.independent && (
        <div className="independent-banner">
          This section runs as a completely independent service. It does not send data to, or
          receive data from, any other section of this platform.
        </div>
      )}

      {stage.limitation && <div className="warning-banner">{stage.limitation}</div>}

      <div className="detail-section">
        <p>{stage.description}</p>
      </div>

      <div className="detail-section">
        <div className="card-title-row" style={{ marginBottom: 12 }}>
          <span className="stage-card-label">Live status</span>
          <StatusBadge status={status} />
        </div>
        {status === 'unavailable' && (
          <p className="info-panel-desc">
            Offline — this service is not currently reachable.{detail ? ` (${detail})` : ''}
          </p>
        )}
      </div>

      <a className="btn btn-primary" href={stage.openUrl} target="_blank" rel="noreferrer">
        {stage.openLabel}
      </a>
    </div>
  );
}
