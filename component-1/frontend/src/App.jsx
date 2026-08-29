import React, { useEffect, useRef, useState } from 'react';
import { checkHealth, predictWaste, analyzeEwaste } from './api.js';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('c1-theme', theme);
}

function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem('c1-theme') || 'dark';
    applyTheme(saved);
    setIsDark(saved === 'dark');
  }, []);

  return (
    <button
      className="theme-toggle"
      onClick={() => {
        const next = isDark ? 'light' : 'dark';
        applyTheme(next);
        setIsDark(!isDark);
      }}
    >
      {isDark ? '☀ Light' : '🌙 Dark'}
    </button>
  );
}

function HealthPill() {
  const [status, setStatus] = useState('pending');

  useEffect(() => {
    let cancelled = false;
    checkHealth()
      .then(() => !cancelled && setStatus('ok'))
      .catch(() => !cancelled && setStatus('bad'));
    return () => {
      cancelled = true;
    };
  }, []);

  const label = status === 'ok' ? 'Backend online' : status === 'bad' ? 'Backend offline' : 'Checking…';
  return (
    <span className="health-pill mono">
      <span className={`dot ${status}`} />
      {label}
    </span>
  );
}

const GRADE_CLASS = { A: 'grade-A', B: 'grade-B', C: 'grade-C' };

function GeneralResult({ data }) {
  return (
    <div className="state-panel">
      <div className="section-label">General waste — result</div>
      <div className="result-grid">
        <div className="result-field">
          <div className="label">Waste type</div>
          <div className="value">{data.waste_type}</div>
        </div>
        <div className="result-field">
          <div className="label">Confidence</div>
          <div className="value">{(data.waste_confidence * 100).toFixed(1)}%</div>
        </div>
        <div className="result-field">
          <div className="label">Condition</div>
          <div className="value">{data.condition}</div>
        </div>
        <div className="result-field">
          <div className="label">Condition confidence</div>
          <div className="value">{(data.condition_confidence * 100).toFixed(1)}%</div>
        </div>
        <div className="result-field">
          <div className="label">Final grade</div>
          <div className={`value ${GRADE_CLASS[data.final_grade] || ''}`}>{data.final_grade}</div>
        </div>
      </div>
    </div>
  );
}

function EwasteResult({ data }) {
  if (!data.detected) {
    return (
      <div className="state-panel">
        <div className="section-label">E-waste — result</div>
        <p>{data.message}</p>
        <p className="mono" style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>
          Confidence threshold: {data.confidence_threshold}
        </p>
      </div>
    );
  }

  const d = data.primary_detection;
  return (
    <div className="state-panel">
      <div className="section-label">E-waste — primary detection</div>
      <div className="result-grid">
        <div className="result-field">
          <div className="label">Detected type</div>
          <div className="value">{d.detected_type}</div>
        </div>
        <div className="result-field">
          <div className="label">Confidence</div>
          <div className="value">{(d.confidence * 100).toFixed(1)}%</div>
        </div>
        <div className="result-field">
          <div className="label">Hazard level</div>
          <div className="value">{d.screening_hazard_level}</div>
        </div>
      </div>

      {d.possible_hazards?.length > 0 && (
        <>
          <div className="section-label">Possible hazards</div>
          <div className="tag-list">
            {d.possible_hazards.map((h) => (
              <span className="tag" key={h}>{h}</span>
            ))}
          </div>
        </>
      )}

      {d.recommended_ppe?.length > 0 && (
        <>
          <div className="section-label">Recommended PPE</div>
          <div className="tag-list">
            {d.recommended_ppe.map((p) => (
              <span className="tag" key={p}>{p}</span>
            ))}
          </div>
        </>
      )}

      {d.handling_instructions?.length > 0 && (
        <>
          <div className="section-label">Handling instructions</div>
          <ul style={{ paddingLeft: 18, fontSize: 13, color: 'var(--text-secondary)' }}>
            {d.handling_instructions.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </>
      )}

      {d.escalation_rule && d.escalation_rule !== 'N/A' && (
        <div className="hazard-banner">Escalation: {d.escalation_rule}</div>
      )}

      {d.certainty_note && d.certainty_note !== 'N/A' && (
        <p className="mono" style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 10 }}>
          {d.certainty_note}
        </p>
      )}

      {data.detections?.length > 1 && (
        <p style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
          {data.detections.length} objects detected in total (showing highest-confidence match above).
        </p>
      )}
    </div>
  );
}

export default function App() {
  const [mode, setMode] = useState('general'); // 'general' | 'ewaste'
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [state, setState] = useState('idle'); // idle | loading | result | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setState('idle');
    setResult(null);
    setError(null);
  }

  function switchMode(next) {
    setMode(next);
    setState('idle');
    setResult(null);
    setError(null);
  }

  async function handleAnalyze() {
    if (!file) return;
    setState('loading');
    setError(null);
    try {
      const data = mode === 'general' ? await predictWaste(file) : await analyzeEwaste(file);
      setResult(data);
      setState('result');
    } catch (err) {
      setError(err.message);
      setState('error');
    }
  }

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <div className="brand-badge">🔎</div>
          <div>
            <div className="brand-title">DETECT</div>
            <div className="brand-sub">AI Waste Assessment</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <HealthPill />
          <ThemeToggle />
        </div>
      </header>

      <main className="main">
        <h1 className="page-title">Identify and assess waste</h1>
        <p className="page-subtitle">
          Upload a photo to classify general waste (type, condition, grade) or screen for
          e-waste devices and their known hazards.
        </p>

        <div className="mode-tabs">
          <div className={`mode-tab ${mode === 'general' ? 'active' : ''}`} onClick={() => switchMode('general')}>
            General Waste
          </div>
          <div className={`mode-tab ${mode === 'ewaste' ? 'active' : ''}`} onClick={() => switchMode('ewaste')}>
            E-Waste
          </div>
        </div>

        <div className="upload-card">
          <label className="upload-label">
            {file ? 'Change image' : 'Choose image'}
            <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} />
          </label>
          {previewUrl && <img className="preview-img" src={previewUrl} alt="Selected upload preview" />}
          <button className="analyze-btn" disabled={!file || state === 'loading'} onClick={handleAnalyze}>
            {state === 'loading' ? (
              <>
                <span className="spinner" />
                Analyzing…
              </>
            ) : (
              'Analyze'
            )}
          </button>
        </div>

        {state === 'error' && <div className="state-panel error">{error}</div>}
        {state === 'result' && result && mode === 'general' && <GeneralResult data={result} />}
        {state === 'result' && result && mode === 'ewaste' && <EwasteResult data={result} />}
      </main>
    </div>
  );
}
