import React from 'react';
import { Link } from 'react-router-dom';
import { STAGES } from '../config.js';

// Purely decorative + navigational: WASTE -> Detect -> Protect -> Process -> Recover.
// The connecting lines carry a subtle one-shot "flow" animation (CSS only).
export default function FlowDiagram() {
  return (
    <div className="flow-diagram" role="img" aria-label="Waste flows through Detect, Protect, Process, and Recover">
      <div className="flow-node flow-node-waste">
        <span className="flow-node-icon">🗑</span>
        <span className="flow-node-label mono">Waste</span>
      </div>

      {STAGES.map((stage, i) => (
        <React.Fragment key={stage.id}>
          <div className="flow-connector" style={{ animationDelay: `${i * 0.15}s` }}>
            <span className="flow-connector-line" />
          </div>
          <Link to={stage.path} className={`flow-node flow-node-stage flow-node-${stage.id}`}>
            <span className="flow-node-label mono">{stage.label}</span>
          </Link>
        </React.Fragment>
      ))}
    </div>
  );
}
