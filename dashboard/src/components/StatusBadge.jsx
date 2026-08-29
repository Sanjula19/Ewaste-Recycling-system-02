import React from 'react';

// Maps the gateway's ping_service() status field to a label/dot class.
// Unknown = gateway itself unreachable, or the service key hasn't reported yet.
const LABELS = {
  ok: 'Online',
  unavailable: 'Offline',
  unhealthy: 'Unhealthy',
  unknown: 'Unknown',
};

export default function StatusBadge({ status }) {
  const s = status || 'unknown';
  return (
    <span className="status-badge">
      <span className={`dot ${s}`} />
      {LABELS[s] || 'Unknown'}
    </span>
  );
}
