import React from 'react';
import SafetyBadge from './SafetyBadge';

export default function ResultCard({ result }) {
  if (!result) return null;

  const metrics = [
    { icon: '⚙️', label: 'Method',      value: result.recommended_method,          color: '#2563EB', bg: '#EFF6FF' },
    { icon: '🌡️', label: 'Temperature', value: `${result.optimal_temp_c}°C`,       color: '#D97706', bg: '#FFFBEB' },
    { icon: '⏱️', label: 'Time',        value: `${result.processing_time_min} min`, color: '#16A34A', bg: '#F0FDF4' },
    { icon: '⚡',  label: 'Energy',     value: `${result.energy_kwh} kWh`,          color: '#EA580C', bg: '#FFF7ED' },
    { icon: '📈',  label: 'Efficiency', value: `${result.recycling_efficiency_pct}%`, color: '#7C3AED', bg: '#F5F3FF' },
    { icon: '☣️',  label: 'Toxicity',   value: result.toxicity_level,               color: '#DC2626', bg: '#FFF5F5' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Safety Banner */}
      <SafetyBadge status={result.safety_status} showFull={true} />

      {/* Pre-drying */}
      {result.pre_drying_required && (
        <div style={{
          padding: '12px 16px', borderRadius: '10px',
          background: '#FFFBEB', border: '1px solid #FDE68A',
          color: '#92400E', fontSize: '13px', fontWeight: '500',
          display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          💧 Pre-drying cycle required before processing
        </div>
      )}

      {/* Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {metrics.map(m => (
          <div key={m.label} style={{
            padding: '18px', borderRadius: '12px',
            border: '1px solid #E8ECF0', background: '#ffffff',
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          }}>
            <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '8px', letterSpacing: '0.1em', fontWeight: '600' }}>
              {m.icon} {m.label.toUpperCase()}
            </div>
            <div style={{
              fontSize: '22px', fontWeight: '700', color: m.color,
              background: m.bg, padding: '6px 10px',
              borderRadius: '8px', display: 'inline-block',
            }}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {/* Chemical Agent */}
      {result.chemical_agent && result.chemical_agent !== 'None' && (
        <div style={{
          padding: '20px', borderRadius: '12px',
          border: '1px solid #DDD6FE', background: '#F5F3FF',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}>
          <div style={{ fontSize: '12px', fontWeight: '600', color: '#7C3AED', letterSpacing: '0.1em', marginBottom: '14px' }}>
            🧪 CHEMICAL AGENT DETAILS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ background: '#ffffff', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Agent</div>
              <div style={{ fontSize: '14px', color: '#7C3AED', fontWeight: '600' }}>{result.chemical_agent}</div>
            </div>
            <div style={{ background: '#ffffff', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Concentration</div>
              <div style={{ fontSize: '14px', color: '#7C3AED', fontWeight: '600' }}>{result.chemical_concentration}</div>
            </div>
            <div style={{ gridColumn: '1/-1', background: '#ffffff', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' }}>Purpose</div>
              <div style={{ fontSize: '13px', color: '#374151' }}>{result.chemical_purpose}</div>
            </div>
            <div style={{ gridColumn: '1/-1', background: '#FFF7ED', padding: '12px', borderRadius: '8px', border: '1px solid #FED7AA' }}>
              <div style={{ fontSize: '11px', color: '#EA580C', marginBottom: '4px', fontWeight: '600' }}>⚠️ Handling Note</div>
              <div style={{ fontSize: '13px', color: '#92400E' }}>{result.handling_note}</div>
            </div>
          </div>
        </div>
      )}

      {/* Input Summary */}
      <div style={{
        padding: '16px 20px', borderRadius: '12px',
        border: '1px solid #E8ECF0', background: '#F9FAFB',
      }}>
        <div style={{ fontSize: '11px', fontWeight: '600', color: '#9CA3AF', letterSpacing: '0.1em', marginBottom: '12px' }}>
          INPUT SUMMARY
        </div>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {[
            ['Material', result.material_name],
            ['Category', result.waste_type],
            ['Weight',   `${result.weight_kg} kg`],
            ['Moisture', result.moisture_condition],
          ].map(([k, v]) => (
            <div key={k}>
              <div style={{ fontSize: '11px', color: '#9CA3AF', marginBottom: '2px' }}>{k}</div>
              <div style={{ fontSize: '14px', color: '#1a1a2e', fontWeight: '600' }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}