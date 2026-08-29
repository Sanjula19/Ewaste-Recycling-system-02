import React, { useState, useEffect, useRef, useCallback } from "react";
import { getLatestReading } from "../services/api";

/* ═══════════════════════════════════════════════════════════════════
   TESTING LAB — Controlled Gas Exposure Data Recorder
   Records real sensor data during controlled chamber experiments,
   labels each reading with the gas type, and exports ML-ready CSV.
   ═══════════════════════════════════════════════════════════════════ */

const GAS_OPTIONS = [
  { value: "CLEAN_AIR", label: "Clean Air (Baseline)",     formula: "—",      color: "var(--val-mq135)", icon: "🌬" },
  { value: "NH3",       label: "NH₃  — Ammonia",           formula: "NH₃",    color: "var(--val-hum)",   icon: "🧪" },
  { value: "LPG",       label: "LPG  — Liquefied Pet. Gas",formula: "C₃H₈",   color: "var(--val-mq2)",   icon: "🔥" },
  { value: "CO",        label: "CO   — Carbon Monoxide",   formula: "CO",     color: "var(--val-mq7)",   icon: "💨" },
  { value: "H2S",       label: "H₂S  — Hydrogen Sulfide",  formula: "H₂S",    color: "var(--alert-warn-text)", icon: "💀" },
  { value: "BENZENE",   label: "C₆H₆ — Benzene",           formula: "C₆H₆",   color: "#c084fc",          icon: "⚗" },
  { value: "SMOKE",     label: "Smoke / E-Waste Fumes",    formula: "Mix",    color: "var(--text-secondary)", icon: "💭" },
];

const PHASES = [
  { value: "BASELINE", label: "Baseline",  note: "Clean air before gas injection",         color: "var(--val-mq135)" },
  { value: "EXPOSURE", label: "Exposure",  note: "Gas present inside chamber",             color: "var(--val-mq7)"   },
  { value: "RECOVERY", label: "Recovery",  note: "After ventilation, returning to normal", color: "var(--val-temp)"  },
];

const formatTime = (sec) => {
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
};

/* ── Small shared components ─────────────────────────────────────── */
const SLabel = ({ children }) => (
  <div style={{
    fontFamily: "JetBrains Mono, monospace", fontSize: "0.6rem",
    fontWeight: 700, color: "var(--field-label-color)",
    textTransform: "uppercase", letterSpacing: "0.14em", marginBottom: "7px",
  }}>{children}</div>
);

const Card = ({ children, style = {}, glow }) => (
  <div className="lab-card" style={{
    padding: "18px 22px", ...style,
    ...(glow ? { boxShadow: glow, borderColor: "rgba(255,23,68,0.4)" } : {}),
  }}>{children}</div>
);

/* ── Live sensor mini-display ────────────────────────────────────── */
const LiveReading = ({ reading }) => {
  if (!reading) return (
    <div style={{
      display: "flex", alignItems: "center", gap: "8px", padding: "14px 0",
      fontFamily: "JetBrains Mono, monospace", fontSize: "0.72rem",
      color: "var(--text-muted)",
    }}>
      <span className="dot-inactive" /> WAITING FOR SENSOR DATA...
    </div>
  );
  const vals = [
    { lbl: "MQ-2",  val: reading.mq2_raw,       col: "var(--val-mq2)"   },
    { lbl: "MQ-7",  val: reading.mq7_raw,        col: "var(--val-mq7)"   },
    { lbl: "MQ-135",val: reading.mq135_raw,      col: "var(--val-mq135)" },
    { lbl: "TEMP",  val: reading.temperature_c != null ? reading.temperature_c.toFixed(1)+"°C" : "—", col: "var(--val-temp)" },
    { lbl: "HUM",   val: reading.humidity_pct  != null ? reading.humidity_pct.toFixed(1)+"%"   : "—", col: "var(--val-hum)"  },
  ];
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", paddingTop: "4px" }}>
      {vals.map(({ lbl, val, col }) => (
        <div key={lbl} style={{ minWidth: "70px" }}>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.55rem", color: "var(--text-muted)", letterSpacing: "0.12em", marginBottom: "3px" }}>{lbl}</div>
          <div style={{
            fontFamily: "JetBrains Mono, monospace", fontSize: "1.05rem",
            fontWeight: 700, color: col,
          }}>{val ?? <span style={{ color: "var(--text-muted)" }}>—</span>}</div>
        </div>
      ))}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════ */
const Testing = () => {
  /* Setup */
  const [gasType,    setGasType]    = useState("CLEAN_AIR");
  const [phase,      setPhase]      = useState("BASELINE");
  const [notes,      setNotes]      = useState("");

  /* Session */
  const sessionId  = useRef(`S${Date.now().toString(36).toUpperCase()}`);
  const seenIds    = useRef(new Set());
  const gasRef     = useRef(gasType);
  const phaseRef   = useRef(phase);
  const notesRef   = useRef(notes);

  /* State */
  const [isRecording,   setIsRecording]   = useState(false);
  const [capturedRows,  setCapturedRows]  = useState([]);
  const [liveReading,   setLiveReading]   = useState(null);
  const [elapsedSec,    setElapsedSec]    = useState(0);
  const [hasStarted,    setHasStarted]    = useState(false);  // session ever started

  /* Keep refs in sync */
  useEffect(() => { gasRef.current   = gasType; }, [gasType]);
  useEffect(() => { phaseRef.current = phase;   }, [phase]);
  useEffect(() => { notesRef.current = notes;   }, [notes]);

  /* ── Elapsed timer ── */
  useEffect(() => {
    if (!isRecording) return;
    const t = setInterval(() => setElapsedSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [isRecording]);

  /* ── Live polling ── */
  useEffect(() => {
    if (!isRecording) return;
    const poll = setInterval(async () => {
      try {
        const res = await getLatestReading();
        const r   = res.data;
        if (r?.reading_id && !seenIds.current.has(r.reading_id)) {
          seenIds.current.add(r.reading_id);
          setCapturedRows(prev => [...prev, {
            ts:    r.received_at,
            did:   r.device_id,
            mq2:   r.mq2_raw,
            mq7:   r.mq7_raw,
            mq135: r.mq135_raw,
            temp:  r.temperature_c,
            hum:   r.humidity_pct,
            gas:   gasRef.current,
            phase: phaseRef.current,
            notes: notesRef.current,
            sid:   sessionId.current,
          }]);
          setLiveReading(r);
        }
      } catch (_) {}
    }, 2500);  // poll every 2.5s (faster than 5s publish rate = fewer missed readings)
    return () => clearInterval(poll);
  }, [isRecording]);

  /* ── Start ── */
  const startRecording = () => {
    setIsRecording(true);
    setHasStarted(true);
  };

  /* ── Stop ── */
  const stopRecording = () => setIsRecording(false);

  /* ── Export labeled CSV ── */
  const exportCSV = () => {
    if (!capturedRows.length) return;
    const headers = ["Timestamp","Device_ID","MQ2_ADC","MQ7_ADC","MQ135_ADC","Temp_C","Humidity_Pct","Gas_Label","Phase","Notes","Session_ID"];
    const body = capturedRows.map(r => [
      new Date(r.ts).toLocaleString(),
      r.did ?? "",
      r.mq2  ?? "",
      r.mq7  ?? "",
      r.mq135 ?? "",
      r.temp != null ? r.temp.toFixed(1) : "",
      r.hum  != null ? r.hum.toFixed(1)  : "",
      r.gas,
      r.phase,
      `"${(r.notes || "").replace(/"/g, "'")}"`,
      r.sid,
    ].join(","));
    const csv  = [headers.join(","), ...body].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = `labeled_${gasRef.current}_${new Date().toISOString().slice(0,10)}_${sessionId.current}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  /* ── Session summary ── */
  const summary = capturedRows.reduce((acc, r) => {
    const k = `${r.gas}|${r.phase}`;
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});

  const gasInfo = GAS_OPTIONS.find(g => g.value === gasType) ?? GAS_OPTIONS[0];
  const phaseInfo = PHASES.find(p => p.value === phase) ?? PHASES[0];

  /* ── Render ── */
  return (
    <div>
      {/* ── Header ── */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-heading)" }}>
            Testing Lab
          </h1>
          <span style={{
            fontFamily: "JetBrains Mono, monospace", fontSize: "0.6rem", fontWeight: 700,
            color: isRecording ? "var(--alert-danger-text)" : "var(--text-accent)",
            background: isRecording ? "rgba(198,40,40,0.12)" : "var(--nav-badge-bg)",
            border: isRecording ? "1px solid rgba(198,40,40,0.3)" : "1px solid var(--nav-badge-border)",
            borderRadius: "4px", padding: "3px 9px", letterSpacing: "0.12em",
          }}>
            {isRecording ? "● REC" : "○ IDLE"}
          </span>
        </div>
        <p style={{
          fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem",
          color: "var(--text-muted)", letterSpacing: "0.08em",
        }}>
          CONTROLLED GAS EXPOSURE RECORDER · AUTO-LABELED ML DATASET BUILDER
        </p>
      </div>

      {/* ── Workflow steps guide ── */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginBottom: "16px",
      }}>
        {[
          { n: "1", label: "SETUP",  desc: "Select gas type, phase, and optional notes" },
          { n: "2", label: "RECORD", desc: "Press Start. Inject gas. Switch phase when needed" },
          { n: "3", label: "EXPORT", desc: "Stop recording. Download ML-ready labeled CSV" },
        ].map(({ n, label, desc }) => (
          <div key={n} style={{
            padding: "12px 14px",
            background: "var(--bg-surface-2)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span style={{
                fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem",
                fontWeight: 700, color: "var(--text-accent)",
                background: "var(--nav-badge-bg)", border: "1px solid var(--nav-badge-border)",
                borderRadius: "4px", padding: "1px 7px",
              }}>{n}</span>
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem", fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.12em" }}>{label}</span>
            </div>
            <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* ── Two-column layout ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>

        {/* ── LEFT: Session Setup ── */}
        <Card>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem", fontWeight: 700, color: "var(--section-label-color)", letterSpacing: "0.14em", marginBottom: "16px" }}>
            SESSION SETUP
          </div>

          {/* Gas type */}
          <SLabel>Gas Type</SLabel>
          <select
            value={gasType}
            onChange={e => setGasType(e.target.value)}
            disabled={isRecording}
            style={{
              width: "100%", marginBottom: "14px",
              padding: "9px 12px",
              borderRadius: "8px",
              border: `1px solid var(--border-normal)`,
              background: "var(--bg-surface-2)",
              color: "var(--text-primary)",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: "0.82rem",
              outline: "none",
              cursor: isRecording ? "not-allowed" : "pointer",
              opacity: isRecording ? 0.6 : 1,
            }}
          >
            {GAS_OPTIONS.map(g => (
              <option key={g.value} value={g.value}>
                {g.icon}  {g.label}
              </option>
            ))}
          </select>

          {/* Chemical formula tag */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <span className={isRecording ? "dot-active" : "dot-inactive"} style={isRecording ? { background: gasInfo.color } : {}} />
            <span style={{
              fontFamily: "JetBrains Mono, monospace", fontSize: "0.78rem",
              fontWeight: 700, color: gasInfo.color,
            }}>
              {gasInfo.icon} {gasInfo.formula} — {gasInfo.label.split("—")[0].trim()}
            </span>
          </div>

          {/* Phase selector */}
          <SLabel>Recording Phase</SLabel>
          <div style={{ display: "flex", gap: "6px", marginBottom: "14px" }}>
            {PHASES.map(p => (
              <button
                key={p.value}
                onClick={() => setPhase(p.value)}
                style={{
                  flex: 1, padding: "8px 4px",
                  borderRadius: "7px",
                  border: `1px solid ${phase === p.value ? p.color : "var(--border-subtle)"}`,
                  background: phase === p.value ? `color-mix(in srgb, ${p.color} 12%, transparent)` : "transparent",
                  color: phase === p.value ? p.color : "var(--text-muted)",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "0.62rem", fontWeight: 700,
                  letterSpacing: "0.08em", cursor: "pointer",
                  transition: "all 0.18s",
                }}
              >
                {p.value}
              </button>
            ))}
          </div>
          <div style={{
            fontFamily: "JetBrains Mono, monospace", fontSize: "0.63rem",
            color: "var(--text-muted)", marginBottom: "14px",
          }}>
            {phaseInfo.note}
          </div>

          {/* Notes */}
          <SLabel>Notes (optional)</SLabel>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="e.g. 2ml NH3 injected via syringe, chamber sealed"
            rows={2}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "8px",
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-surface-2)",
              color: "var(--text-primary)",
              fontFamily: "Space Grotesk, sans-serif",
              fontSize: "0.8rem",
              outline: "none",
              resize: "vertical",
            }}
          />
        </Card>

        {/* ── RIGHT: Recording control ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>

          {/* Status card */}
          <Card
            style={{ flex: 1 }}
            glow={isRecording ? "0 0 20px rgba(198,40,40,0.25)" : undefined}
          >
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem", fontWeight: 700, color: "var(--section-label-color)", letterSpacing: "0.14em", marginBottom: "12px" }}>
              RECORDING STATUS
            </div>

            {/* Status row */}
            <div style={{ display: "flex", gap: "24px", marginBottom: "14px" }}>
              <div>
                <SLabel>Status</SLabel>
                <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                  {isRecording
                    ? <><span className="dot-active" style={{ background: "var(--alert-danger-text)", boxShadow: "0 0 8px rgba(198,40,40,0.7)" }} />
                        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", fontWeight: 700, color: "var(--alert-danger-text)" }}>RECORDING</span></>
                    : <><span className="dot-inactive" />
                        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "var(--text-muted)" }}>IDLE</span></>
                  }
                </div>
              </div>
              <div>
                <SLabel>Elapsed</SLabel>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.2rem", fontWeight: 700, color: isRecording ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {formatTime(elapsedSec)}
                </div>
              </div>
              <div>
                <SLabel>Captured</SLabel>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.2rem", fontWeight: 700, color: "var(--text-accent)" }}>
                  {capturedRows.length}
                </div>
              </div>
            </div>

            {/* Live sensor values */}
            <SLabel>Live Sensor Values</SLabel>
            <LiveReading reading={liveReading} />
          </Card>

          {/* Control buttons */}
          <div style={{ display: "flex", gap: "10px" }}>
            {!isRecording ? (
              <button
                onClick={startRecording}
                style={{
                  flex: 1, padding: "13px",
                  borderRadius: "9px",
                  border: "1px solid var(--text-accent)",
                  background: "rgba(0,200,83,0.1)",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "0.82rem", fontWeight: 700,
                  letterSpacing: "0.12em",
                  color: "var(--text-accent)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                ▶ START RECORDING
              </button>
            ) : (
              <button
                onClick={stopRecording}
                style={{
                  flex: 1, padding: "13px",
                  borderRadius: "9px",
                  border: "1px solid var(--alert-danger-text)",
                  background: "rgba(198,40,40,0.1)",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "0.82rem", fontWeight: 700,
                  letterSpacing: "0.12em",
                  color: "var(--alert-danger-text)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                ■ STOP RECORDING
              </button>
            )}
            {capturedRows.length > 0 && (
              <button
                onClick={exportCSV}
                style={{
                  flex: 1, padding: "13px",
                  borderRadius: "9px",
                  border: "1px solid var(--border-accent)",
                  background: "var(--nav-badge-bg)",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "0.82rem", fontWeight: 700,
                  letterSpacing: "0.10em",
                  color: "var(--text-accent)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                ⬇ EXPORT LABELED CSV
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Session Summary ── */}
      {Object.keys(summary).length > 0 && (
        <Card style={{ marginTop: "14px" }}>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem", fontWeight: 700, color: "var(--section-label-color)", letterSpacing: "0.14em", marginBottom: "14px" }}>
            SESSION SUMMARY — {sessionId.current}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {Object.entries(summary).map(([key, count]) => {
              const [gas, ph] = key.split("|");
              const ginfo = GAS_OPTIONS.find(g => g.value === gas);
              const pinfo = PHASES.find(p => p.value === ph);
              return (
                <div key={key} style={{
                  padding: "9px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-surface-2)",
                  border: `1px solid var(--border-subtle)`,
                  minWidth: "140px",
                }}>
                  <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.6rem", color: ginfo?.color ?? "var(--text-accent)", fontWeight: 700, letterSpacing: "0.1em", marginBottom: "3px" }}>
                    {ginfo?.icon} {gas}
                  </div>
                  <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--text-muted)", marginBottom: "6px" }}>{ph}</div>
                  <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {count} <span style={{ fontSize: "0.65rem", fontWeight: 400, color: "var(--text-muted)" }}>rows</span>
                  </div>
                </div>
              );
            })}
            <div style={{
              padding: "9px 14px",
              borderRadius: "8px",
              background: "var(--nav-badge-bg)",
              border: "1px solid var(--nav-badge-border)",
              minWidth: "120px",
              display: "flex", flexDirection: "column", justifyContent: "center",
            }}>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--text-muted)", marginBottom: "4px" }}>TOTAL</div>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.5rem", fontWeight: 700, color: "var(--text-accent)" }}>
                {capturedRows.length}
              </div>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--text-muted)" }}>labeled rows</div>
            </div>
          </div>
        </Card>
      )}

      {/* ── Data preview table ── */}
      {capturedRows.length > 0 && (
        <Card style={{ marginTop: "14px", padding: 0, overflow: "hidden" }}>
          <div style={{
            padding: "12px 18px",
            borderBottom: "1px solid var(--border-divider)",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "0.62rem", fontWeight: 700,
            color: "var(--section-label-color)", letterSpacing: "0.14em",
          }}>
            CAPTURED DATA PREVIEW — LAST {Math.min(10, capturedRows.length)} OF {capturedRows.length} ROWS
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  {["TIMESTAMP","MQ-2","MQ-7","MQ-135","TEMP","HUM","GAS LABEL","PHASE"].map(h => (
                    <th key={h} style={{
                      padding: "10px 13px", textAlign: "left",
                      fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem",
                      fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
                      color: "var(--table-header-text)", background: "var(--table-header-bg)",
                      whiteSpace: "nowrap",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {capturedRows.slice(-10).reverse().map((r, i) => {
                  const ginfo = GAS_OPTIONS.find(g => g.value === r.gas);
                  const pinfo = PHASES.find(p => p.value === r.phase);
                  return (
                    <tr key={i} style={{
                      borderBottom: "1px solid var(--table-divider)",
                      background: i % 2 === 0 ? "var(--table-row-a)" : "var(--table-row-b)",
                    }}>
                      <td style={{ padding: "9px 13px", fontFamily: "JetBrains Mono, monospace", fontSize: "0.7rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                        {new Date(r.ts).toLocaleTimeString()}
                      </td>
                      {[
                        { v: r.mq2,   c: "var(--val-mq2)"   },
                        { v: r.mq7,   c: "var(--val-mq7)"   },
                        { v: r.mq135, c: "var(--val-mq135)" },
                        { v: r.temp  != null ? r.temp.toFixed(1)  : null, c: "var(--val-temp)" },
                        { v: r.hum   != null ? r.hum.toFixed(1)   : null, c: "var(--val-hum)"  },
                      ].map(({ v, c }, ci) => (
                        <td key={ci} style={{ padding: "9px 13px", fontFamily: "JetBrains Mono, monospace", fontSize: "0.85rem", fontWeight: 700, color: v != null ? c : "var(--text-muted)" }}>
                          {v ?? "—"}
                        </td>
                      ))}
                      <td style={{ padding: "9px 13px" }}>
                        <span style={{
                          fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem", fontWeight: 700,
                          color: ginfo?.color ?? "var(--text-accent)",
                          background: "var(--bg-surface-2)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px", padding: "2px 8px",
                          letterSpacing: "0.08em",
                        }}>
                          {ginfo?.icon} {r.gas}
                        </span>
                      </td>
                      <td style={{ padding: "9px 13px" }}>
                        <span style={{
                          fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem",
                          color: pinfo?.color ?? "var(--text-secondary)",
                        }}>
                          {r.phase}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── ML guidance ── */}
      <div style={{
        marginTop: "14px", padding: "14px 18px",
        background: "var(--notice-bg)",
        border: "1px solid var(--notice-border-color)",
        borderLeft: "3px solid var(--notice-left-color)",
        borderRadius: "8px",
      }}>
        <div style={{
          fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem",
          fontWeight: 700, color: "var(--notice-icon)", letterSpacing: "0.12em",
          marginBottom: "8px",
        }}>⚗ ML DATASET COLLECTION GUIDE</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
          {[
            { label: "Minimum per class", value: "80 rows", note: "e.g. 80 NH3, 80 LPG, 80 CLEAN_AIR" },
            { label: "Recommended target", value: "150+ rows", note: "More data = better model accuracy" },
            { label: "Time @ 5s intervals", value: "~12 min", note: "to capture 150 rows per gas type" },
          ].map(({ label, value, note }) => (
            <div key={label}>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--notice-text)", letterSpacing: "0.1em", marginBottom: "3px", textTransform: "uppercase" }}>{label}</div>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.9rem", fontWeight: 700, color: "var(--notice-icon)", marginBottom: "2px" }}>{value}</div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "0.72rem", color: "var(--notice-text)", lineHeight: 1.5 }}>{note}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Testing;
