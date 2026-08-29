import React from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from './StatusBadge.jsx';

export default function ComponentCard({ component, status }) {
  return (
    <div className="card">
      <div className="card-title-row">
        <span className="card-title">{component.name}</span>
        <StatusBadge status={status} />
      </div>
      <span className="card-owner">Owner: {component.owner}</span>
      <span className="card-desc">{component.description}</span>
      <span className="workflow-tag">{component.workflow}</span>
      <div className="card-footer">
        <Link className="btn" to={component.path}>
          Details
        </Link>
        <a className="btn btn-primary" href={component.openUrl} target="_blank" rel="noreferrer">
          {component.openLabel}
        </a>
      </div>
    </div>
  );
}
