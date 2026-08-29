import React from 'react';

const SAFETY = {
  CRITICAL: { color: '#DC2626', bg: '#FEF2F2', border: '#FECACA', icon: '⛔', text: 'CRITICAL — Immediate Action Required' },
  WARNING:  { color: '#D97706', bg: '#FFFBEB', border: '#FDE68A', icon: '⚠️', text: 'WARNING — Proceed with Caution' },
  SECURE:   { color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0', icon: '✅', text: 'SECURE — Safe to Process' },
};

export default function SafetyBadge({ status, showFull = false }) {
  const s = SAFETY[status] || SAFETY.SECURE;

  if (!showFull) {
    return (
      <span style={{
        padding: '3px 10px', borderRadius: '20px', fontSize: '11px',
        fontWeight: '600', color: s.color,
        background: s.bg, border: `1px solid ${s.border}`,
      }}>
        {s.icon} {status}
      </span>
    );
  }

  return (
    <div style={{
      padding: '16px 20px', borderRadius: '12px',
      border: `1px solid ${s.border}`, background: s.bg,
      display: 'flex', alignItems: 'center', gap: '14px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    }}>
      <span style={{ fontSize: '28px' }}>{s.icon}</span>
      <div>
        <div style={{ fontSize: '16px', fontWeight: '700', color: s.color }}>{s.text}</div>
        <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px' }}>
          Safety status: {status}
        </div>
      </div>
    </div>
  );
}