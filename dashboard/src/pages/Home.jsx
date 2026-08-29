import React from 'react';
import { STAGES, GATEWAY_URL } from '../config.js';
import { useGatewayHealth } from '../useGatewayHealth.js';
import FlowDiagram from '../components/FlowDiagram.jsx';
import StageCard from '../components/StageCard.jsx';

export default function Home() {
  const health = useGatewayHealth();

  return (
    <div>
      <section className="hero">
        <h1 className="hero-title">One platform for e-waste recycling and safety</h1>
        <p className="hero-statement">
          From the moment waste arrives to the moment recovered material is sold, this platform
          detects what it is, protects the people handling it, processes it correctly, and
          recovers its value.
        </p>
        <FlowDiagram />
      </section>

      {!health.loading && !health.gatewayReachable && (
        <div className="warning-banner">
          API Gateway unreachable at <code>{GATEWAY_URL}</code>. Live status below will show as
          Unknown until it's running.
        </div>
      )}

      <section>
        <h2 className="section-heading">Platform sections</h2>
        <div className="stage-grid">
          {STAGES.map((stage, i) => (
            <StageCard
              key={stage.id}
              stage={stage}
              index={i}
              status={health.gatewayReachable ? health.services[stage.componentKey]?.status : 'unknown'}
            />
          ))}
        </div>
      </section>

      <section className="info-row">
        <div className="info-panel">
          <h3>System status</h3>
          <p className="info-panel-desc">Live, from the API Gateway's own health check.</p>
          <ul className="status-list">
            {STAGES.map((stage) => {
              const s = health.gatewayReachable ? health.services[stage.componentKey]?.status : 'unknown';
              return (
                <li key={stage.id}>
                  <span className={`dot ${s || 'unknown'}`} />
                  {stage.label}
                  <span className="status-list-value mono">
                    {!health.gatewayReachable ? 'Unknown' : s === 'ok' ? 'Online' : s === 'unavailable' ? 'Offline' : s === 'unhealthy' ? 'Unhealthy' : 'Unknown'}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="info-panel">
          <h3>Recent activity</h3>
          <p className="info-panel-desc">
            No data — a unified activity feed across Detect → Process → Recover requires the
            cross-service workflow, which has not been built yet.
          </p>
          <div className="empty-state mono">Waiting</div>
        </div>

        <div className="info-panel">
          <h3>Quick actions</h3>
          <div className="quick-actions">
            {STAGES.map((stage) => (
              <a key={stage.id} className="quick-action" href={stage.openUrl} target="_blank" rel="noreferrer">
                {stage.openLabel}
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
