import React, { useState, useEffect, useCallback } from "react";
import { getLatestReading, getDashboardStats } from "../services/api";

const POLL_MS = 5000;

/* ─── Shared card ──────────────────────────────────────────────────── */
const Card = ({ children, style = {} }) => (
  <div className="lab-card" style={{ padding: "18px 22px", ...style }}>
    {children}
  </div>
);

/* ─── Section divider label ────────────────────────────────────────── */
const SectionLabel = ({ children }) => (
  <div style={{
    display:       "flex",
    alignItems:    "center",
    gap:           "10px",
    marginBottom:  "10px",
    marginTop:     "6px",
  }}>
    <span style={{ flex: 1, height: "1px", background: "var(--section-line-color)" }} />
    <span style={{
      fontFamily:    "JetBrains Mono, monospace",
      fontSize:      "0.62rem",
      fontWeight:    700,
      color:         "var(--section-label-color)",
      letterSpacing: "0.18em",
      textTransform: "uppercase",
      whiteSpace:    "nowrap",
    }}>{children}</span>
    <span style={{ flex: 1, height: "1px", background: "var(--section-line-color)" }} />
  </div>
);

/* ─── Small field label ────────────────────────────────────────────── */
const FieldLabel = ({ children }) => (
  <div style={{
    fontFamily:    "JetBrains Mono, monospace",
    fontSize:      "0.6rem",
    fontWeight:    700,
    color:         "var(--field-label-color)",
    textTransform: "uppercase",
    letterSpacing: "0.14em",
    marginBottom:  "6px",
  }}>{children}</div>
);

/* ─── Big sensor value ─────────────────────────────────────────────── */
const SensorValue = ({ children, unit, valVar, glowVar }) => (
  <div style={{ display: "flex", alignItems: "baseline", gap: "5px", lineHeight: 1 }}>
    <span style={{
      fontFamily:  "JetBrains Mono, monospace",
      fontSize:    "2.1rem",
      fontWeight:  700,
      color:       `var(${valVar})`,
      textShadow:  `var(${glowVar})`,
    }}>{children}</span>
    {unit && (
      <span style={{
        fontFamily:    "JetBrains Mono, monospace",
        fontSize:      "0.75rem",
        fontWeight:    600,
        color:         "var(--field-mono-sub)",
        letterSpacing: "0.08em",
      }}>{unit}</span>
    )}
  </div>
);

/* ─── Not connected indicator ──────────────────────────────────────── */
const NotConnected = () => (
  <div style={{ display: "flex", alignItems: "center", gap: "7px", paddingTop: "2px" }}>
    <span className="dot-inactive" />
    <span style={{
      fontFamily:    "JetBrains Mono, monospace",
      fontSize:      "0.78rem",
      color:         "var(--dot-inactive-bg)",
      letterSpacing: "0.08em",
    }}>NOT CONNECTED</span>
  </div>
);

/* ─── Sensor card ──────────────────────────────────────────────────── */
const SensorCard = ({ label, subtitle, valVar, glowVar, accentVar, dotActive, value, unit, children }) => (
  <Card style={{ borderLeft: `3px solid var(${accentVar})` }}>
    <div style={{
      display:        "flex",
      justifyContent: "space-between",
      alignItems:     "flex-start",
      marginBottom:   "2px",
    }}>
      <FieldLabel>{label}</FieldLabel>
      {dotActive
        ? <span className="dot-active" style={{ background: `var(${valVar})`, boxShadow: `var(${glowVar})` }} />
        : <span className="dot-inactive" />}
    </div>
    <div style={{
      fontFamily:    "JetBrains Mono, monospace",
      fontSize:      "0.6rem",
      color:         "var(--field-mono-sub)",
      letterSpacing: "0.06em",
      marginBottom:  "10px",
    }}>{subtitle}</div>
    {value != null
      ? <SensorValue unit={unit} valVar={valVar} glowVar={glowVar}>{value}</SensorValue>
      : <NotConnected />}
    {children}
  </Card>
);

/* ─── Monitor page ─────────────────────────────────────────────────── */
const Monitor = () => {
  const [reading,     setReading]     = useState(null);
  const [stats,       setStats]       = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [noData,      setNoData]      = useState(false);
  const [loading,     setLoading]     = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [rRes, sRes] = await Promise.allSettled([
        getLatestReading(),
        getDashboardStats(),
      ]);
      if (rRes.status === "fulfilled") {
        setReading(rRes.value.data);
        setNoData(false);
        setLastUpdated(new Date());
      } else {
        setNoData(rRes.reason?.response?.status === 404);
        setReading(null);
      }
      if (sRes.status === "fulfilled") setStats(sRes.value.data);
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, POLL_MS);
    return () => clearInterval(t);
  }, [fetchAll]);

  /* ── Loading ── */
  if (loading) return (
    <div style={{ textAlign: "center", padding: "80px 24px" }}>
      <div style={{
        fontFamily:    "JetBrains Mono, monospace",
        fontSize:      "0.8rem",
        color:         "var(--text-accent)",
        letterSpacing: "0.18em",
      }}>
        INITIALIZING SENSOR ARRAY...
      </div>
    </div>
  );

  /* ── No data ── */
  if (noData || !reading) return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-heading)", marginBottom: "4px" }}>
          Live Monitor
        </h1>
        <p style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.67rem", color: "var(--text-muted)", letterSpacing: "0.1em",
        }}>
          REAL-TIME SENSOR ARRAY · AUTO-REFRESH {POLL_MS / 1000}s
        </p>
      </div>
      <div className="lab-card" style={{ padding: "64px 48px", textAlign: "center" }}>
        <div style={{ fontSize: "2.6rem", marginBottom: "14px", opacity: 0.5 }}>📡</div>
        <div style={{
          fontFamily:    "JetBrains Mono, monospace",
          fontSize:      "0.82rem", fontWeight: 700,
          color:         "var(--text-accent)", letterSpacing: "0.14em",
          marginBottom:  "10px",
        }}>AWAITING ESP32 SIGNAL</div>
        <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", maxWidth: "360px", margin: "0 auto", lineHeight: 1.6 }}>
          Power on the ESP32 and confirm it is publishing to{" "}
          <code style={{
            fontFamily:    "JetBrains Mono, monospace",
            background:    "var(--bg-code)",
            padding:       "2px 6px",
            borderRadius:  "4px",
            fontSize:      "0.78rem",
            color:         "var(--text-code)",
            border:        "1px solid var(--border-subtle)",
          }}>ewaste/esp32/sensors</code>
        </div>
      </div>
    </div>
  );

  const mqttOk = stats?.mqtt_connected ?? false;

  return (
    <div style={{ animation: "fade-up 0.3s ease" }}>

      {/* ── Page header ── */}
      <div style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-heading)", marginBottom: "3px" }}>
            Live Monitor
          </h1>
          <p style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.09em",
          }}>
            E-WASTE WORKER SAFETY · REAL-TIME SENSOR DATA · AUTO-REFRESH {POLL_MS / 1000}s
          </p>
        </div>
        <span style={{
          fontFamily:    "JetBrains Mono, monospace",
          fontSize:      "0.62rem", fontWeight: 700,
          color:         "var(--text-accent)",
          letterSpacing: "0.12em",
          background:    "var(--nav-badge-bg)",
          border:        "1px solid var(--nav-badge-border)",
          borderRadius:  "4px",
          padding:       "3px 9px",
          marginBottom:  "18px",
        }}>● LIVE</span>
      </div>

      {/* ── Status bar ── */}
      <div className="lab-card" style={{
        padding:      "12px 20px",
        marginBottom: "14px",
        borderLeft:   `3px solid ${mqttOk ? "var(--text-accent)" : "var(--border-subtle)"}`,
        display:      "flex",
        flexWrap:     "wrap",
        gap:          "24px",
        alignItems:   "center",
        position:     "relative",
        overflow:     "hidden",
      }}>
        {/* Decorative formula watermark */}
        <span aria-hidden="true" style={{
          position:      "absolute", right: "18px", top: "50%",
          transform:     "translateY(-50%)",
          fontFamily:    "JetBrains Mono, monospace",
          fontSize:      "0.58rem", color: "var(--section-line-color)",
          letterSpacing: "0.08em", userSelect: "none",
        }}>H₂S · CO · NH₃ · C₆H₆</span>

        {[
          { label: "Device",        value: reading.device_id },
          { label: "MQTT",          value: mqttOk ? "● CONNECTED" : "○ WAITING",
            color: mqttOk ? "var(--text-accent)" : "var(--text-muted)" },
          { label: "Total Readings",value: (stats?.total_readings ?? 0).toLocaleString() },
          { label: "Last Received", value: lastUpdated
              ? lastUpdated.toLocaleTimeString()
              : new Date(reading.received_at).toLocaleTimeString() },
        ].map(({ label, value, color }) => (
          <div key={label}>
            <FieldLabel>{label}</FieldLabel>
            <span style={{
              fontFamily:    "JetBrains Mono, monospace",
              fontSize:      "0.82rem",
              fontWeight:    600,
              color:         color ?? "var(--text-primary)",
              letterSpacing: "0.04em",
            }}>{value}</span>
          </div>
        ))}
      </div>

      {/* ── Environment sensors ── */}
      <SectionLabel>Environmental Conditions · DHT22</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>

        <Card style={{ borderLeft: "3px solid var(--accent-temp)" }}>
          <FieldLabel>Temperature</FieldLabel>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.59rem", color: "var(--field-mono-sub)", letterSpacing: "0.06em", marginBottom: "10px" }}>
            AMBIENT · DHT22 SENSOR
          </div>
          {reading.temperature_c != null
            ? <SensorValue unit="°C" valVar="--val-temp" glowVar="--glow-temp">{reading.temperature_c.toFixed(1)}</SensorValue>
            : <NotConnected />}
        </Card>

        <Card style={{ borderLeft: "3px solid var(--accent-hum)" }}>
          <FieldLabel>Humidity</FieldLabel>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.59rem", color: "var(--field-mono-sub)", letterSpacing: "0.06em", marginBottom: "10px" }}>
            RELATIVE HUMIDITY · DHT22 SENSOR
          </div>
          {reading.humidity_pct != null
            ? <SensorValue unit="%" valVar="--val-hum" glowVar="--glow-hum">{reading.humidity_pct.toFixed(1)}</SensorValue>
            : <NotConnected />}
        </Card>
      </div>

      {/* ── Gas sensors ── */}
      <SectionLabel>Gas Sensor Array · Raw ADC (0 – 4095)</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>

        <SensorCard
          label="MQ-2"
          subtitle="LPG · SMOKE · FLAMMABLE GAS"
          valVar="--val-mq2" glowVar="--glow-mq2" accentVar="--accent-mq2"
          dotActive={reading.mq2_raw != null}
          value={reading.mq2_raw} unit="ADC"
        >
          <div style={{ marginTop: "10px", fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--field-mono-sub)", letterSpacing: "0.06em" }}>
            ↑ HIGHER = MORE GAS
          </div>
        </SensorCard>

        <SensorCard
          label="MQ-7"
          subtitle="CO · CARBON MONOXIDE · TOXIC"
          valVar="--val-mq7" glowVar="--glow-mq7" accentVar="--accent-mq7"
          dotActive={reading.mq7_raw != null}
          value={reading.mq7_raw} unit="ADC"
        >
          <div style={{ marginTop: "10px", fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--field-mono-sub)", letterSpacing: "0.06em" }}>
            ↑ HIGHER = MORE CO
          </div>
        </SensorCard>

        <SensorCard
          label="MQ-135"
          subtitle="NH₃ · BENZENE · VOC · AIR QUALITY"
          valVar="--val-mq135" glowVar="--glow-mq135" accentVar="--accent-mq135"
          dotActive={reading.mq135_raw != null}
          value={reading.mq135_raw} unit="ADC"
        >
          <div style={{ marginTop: "10px", fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem", color: "var(--field-mono-sub)", letterSpacing: "0.06em" }}>
            ↑ HIGHER = MORE VOC
          </div>
        </SensorCard>
      </div>

      {/* ── Research notice ── */}
      <div style={{
        marginTop:   "14px",
        padding:     "12px 18px",
        background:  "var(--notice-bg)",
        border:      "1px solid var(--notice-border-color)",
        borderLeft:  "3px solid var(--notice-left-color)",
        borderRadius: "8px",
        display:     "flex",
        alignItems:  "flex-start",
        gap:         "10px",
      }}>
        <span style={{ color: "var(--notice-icon)", fontSize: "0.9rem", marginTop: "1px", flexShrink: 0 }}>⚠</span>
        <span style={{
          fontFamily:    "JetBrains Mono, monospace",
          fontSize:      "0.66rem",
          color:         "var(--notice-text)",
          letterSpacing: "0.03em",
          lineHeight:    1.65,
        }}>
          PROTOTYPE RESEARCH SYSTEM · Values shown are raw 12-bit ADC outputs (0–4095).
          ADC-to-ppm conversion requires individual sensor calibration constants.
          Do not use for occupational safety decisions without calibrated ppm measurements.
        </span>
      </div>
    </div>
  );
};

export default Monitor;
