import React, { useState } from 'react';

const MATERIALS = {
  Metal:     ['Aluminum', 'Steel', 'Scrap Steel', 'Sheet Metal', 'Lead-Based Alloy'],
  Plastic:   ['Polypropylene', 'Plastic Resin', 'Reprocessed Plastics', 'Packaging'],
  'E-waste': ['Circuit Board', 'Machine Component'],
  Organic:   ['Cotton', 'Textiles'],
  Chemical:  ['Solvent', 'Industrial Oil', 'Coolant', 'Catalyst'],
};

const CAT_COLORS = {
  Metal:     { color: '#2563EB', bg: '#EFF6FF', border: '#BFDBFE' },
  Plastic:   { color: '#D97706', bg: '#FFFBEB', border: '#FDE68A' },
  'E-waste': { color: '#DC2626', bg: '#FFF5F5', border: '#FECACA' },
  Organic:   { color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0' },
  Chemical:  { color: '#7C3AED', bg: '#F5F3FF', border: '#DDD6FE' },
};

export default function InputForm({ onSubmit, loading }) {
  const [category, setCategory] = useState('E-waste');
  const [material, setMaterial] = useState('Circuit Board');
  const [weight,   setWeight]   = useState(5);
  const [moisture, setMoisture] = useState('Wet');

  const cc = CAT_COLORS[category] || CAT_COLORS.Metal;

  const handleSubmit = () => {
    if (typeof onSubmit === 'function') {
      onSubmit({
        material_name     : material,
        waste_type        : category,
        weight_kg         : parseFloat(weight),
        moisture_condition: moisture,
      });
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <label style={{ fontSize: '12px', fontWeight: '600', color: '#374151', letterSpacing: '0.08em', display: 'block', marginBottom: '10px' }}>
          WASTE CATEGORY
        </label>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {Object.keys(MATERIALS).map(cat => {
            const c = CAT_COLORS[cat];
            const active = category === cat;
            return (
              <button key={cat}
                onClick={() => { setCategory(cat); setMaterial(MATERIALS[cat][0]); }}
                style={{
                  padding: '8px 18px', borderRadius: '20px', cursor: 'pointer',
                  border: `1.5px solid ${active ? c.color : '#E5E7EB'}`,
                  background: active ? c.bg : '#ffffff',
                  color: active ? c.color : '#6B7280',
                  fontSize: '13px', fontFamily: 'inherit',
                  fontWeight: active ? '600' : '400', transition: 'all 0.2s',
                }}>
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
        <div>
          <label style={{ fontSize: '12px', fontWeight: '600', color: '#374151', letterSpacing: '0.08em', display: 'block', marginBottom: '8px' }}>
            MATERIAL
          </label>
          <select value={material} onChange={e => setMaterial(e.target.value)} style={{
            width: '100%', padding: '11px 14px', borderRadius: '10px',
            border: `1.5px solid ${cc.border}`,
            background: '#ffffff', color: '#1a1a2e',
            fontSize: '14px', fontFamily: 'inherit', outline: 'none', cursor: 'pointer',
          }}>
            {MATERIALS[category].map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '12px', fontWeight: '600', color: '#374151', letterSpacing: '0.08em', display: 'block', marginBottom: '8px' }}>
            MOISTURE CONDITION
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {['Dry', 'Wet'].map(m => (
              <button key={m} onClick={() => setMoisture(m)} style={{
                padding: '11px', borderRadius: '10px', cursor: 'pointer',
                border: `1.5px solid ${moisture === m ? cc.color : '#E5E7EB'}`,
                background: moisture === m ? cc.bg : '#ffffff',
                color: moisture === m ? cc.color : '#6B7280',
                fontSize: '14px', fontFamily: 'inherit',
                fontWeight: moisture === m ? '600' : '400', transition: 'all 0.2s',
              }}>
                {m === 'Dry' ? '☀️ Dry' : '💧 Wet'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: '28px' }}>
        <label style={{ fontSize: '12px', fontWeight: '600', color: '#374151', letterSpacing: '0.08em', display: 'block', marginBottom: '8px' }}>
          WEIGHT — <span style={{ color: cc.color }}>{weight} kg</span>
        </label>
        <input type="range" min="0.5" max="25" step="0.5"
          value={weight} onChange={e => setWeight(e.target.value)}
          style={{ width: '100%', accentColor: cc.color, cursor: 'pointer' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
          <span>0.5 kg</span><span>25.0 kg</span>
        </div>
      </div>

      <button onClick={handleSubmit} disabled={loading} style={{
        width: '100%', padding: '14px', borderRadius: '12px',
        border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
        background: loading ? '#E5E7EB' : 'linear-gradient(135deg, #2563EB, #7C3AED)',
        color: loading ? '#9CA3AF' : '#ffffff',
        fontSize: '15px', fontFamily: 'inherit', fontWeight: '700',
        letterSpacing: '0.05em', transition: 'all 0.2s',
        boxShadow: loading ? 'none' : '0 4px 14px rgba(37,99,235,0.3)',
      }}>
        {loading ? '⏳ Processing...' : '⚡ GENERATE PROCESS RECIPE'}
      </button>
    </div>
  );
}