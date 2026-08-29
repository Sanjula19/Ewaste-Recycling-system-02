import React from 'react';
import { STAGES } from '../config.js';

// Honest history page: this platform has no shared, cross-section activity
// log yet (that would require the C1 -> C3 -> C4 workflow, which is not
// built — see integration/INTEGRATION_STATUS.md). Rather than fabricate one,
// this links to whatever history/history-like feature already exists inside
// each section's own application.
const NOTES = {
  detect: 'No dedicated history view — each analysis is a single request/response and nothing is stored centrally.',
  protect: "Has its own History page (readings, trials, export) inside its dashboard — open it below.",
  process: 'Currently runs on the same backend as Protect, so the same readings/trials/export history exists there — but not a process-optimization history yet.',
  recover: 'Has its own manifest summary and cycle history inside its dashboard — open it below.',
};

export default function History() {
  return (
    <div>
      <h1 className="page-title">History</h1>
      <p className="page-subtitle">
        No unified activity log exists across sections yet. Each section's own history lives
        inside its own application.
      </p>

      <div className="stage-grid">
        {STAGES.map((stage) => (
          <div className="stage-card" key={stage.id}>
            <div className="stage-card-top">
              <span className="stage-card-label">{stage.label}</span>
            </div>
            <p className="stage-card-desc">{NOTES[stage.id]}</p>
            <div className="stage-card-actions">
              <a className="btn btn-primary" href={stage.openUrl} target="_blank" rel="noreferrer">
                {stage.openLabel}
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
