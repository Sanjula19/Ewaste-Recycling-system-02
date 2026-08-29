import React from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from './StatusBadge.jsx';

export default function StageCard({ stage, status, index }) {
  return (
    <div className="stage-card" style={{ animationDelay: `${index * 0.08}s` }}>
      <div className="stage-card-top">
        <span className="stage-card-label">{stage.label}</span>
        <StatusBadge status={status} />
      </div>
      <p className="stage-card-tagline">{stage.tagline}</p>
      <p className="stage-card-desc">{stage.description}</p>
      {stage.independent && <span className="chip chip-info">Independent service</span>}
      <div className="stage-card-actions">
        <Link className="btn" to={stage.path}>
          Details
        </Link>
        <a className="btn btn-primary" href={stage.openUrl} target="_blank" rel="noreferrer">
          {stage.openLabel}
        </a>
      </div>
    </div>
  );
}
