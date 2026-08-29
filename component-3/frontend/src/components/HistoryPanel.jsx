import React from 'react';
import SafetyBadge from './SafetyBadge';

export default function HistoryPanel({ history }) {
  if (!history || history.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: '#9CA3AF' }}>
        <div style={{ fontSize: '40px', marginBottom: '12px' }}>📜</div>
        <div style={{ fontSize: '16px', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>No history yet</div>
        <div style={{ fontSize: '14px' }}>Run an optimization to see results here</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ fontSize: '12px', fontWeight: '600', color: '#9CA3AF', letterSpacing: '0.08em', marginBottom: '4px' }}>
        {history.length} RECORDS
      </div>
      {history.map((h, i) => (
        <div key={i} style={{
          padding: '14px 18px', borderRadius: '10px',
          border: '1px solid #E8ECF0', background: '#ffffff',
          display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr auto',
          alignItems: 'center', gap: '16px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}>
          <div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Material</div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a2e' }}>{h.material_name}</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Method</div>
            <div style={{ fontSize: '14px', color: '#2563EB', fontWeight: '500' }}>{h.recommended_method}</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Weight</div>
            <div style={{ fontSize: '14px', color: '#374151' }}>{h.weight_kg} kg</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>Energy</div>
            <div style={{ fontSize: '14px', color: '#374151' }}>{h.energy_kwh} kWh</div>
          </div>
          <SafetyBadge status={h.safety_status} />
        </div>
      ))}
    </div>
  );
}