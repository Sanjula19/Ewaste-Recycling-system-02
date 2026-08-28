import React, { useState, useEffect, useCallback, useRef } from "react";
import { getAlerts, acknowledgeAlert } from "../services/api";

const GAS_ICONS = { LPG: "🔥", CO: "💨", BENZENE: "⚗", AMMONIA: "🧪", H2S: "💀", default: "⚠" };

/* ─── Risk level style tokens (pure CSS-var references) ────────────── */
const riskTokens = (rl) => rl === "RED"
  ? {
      topBar:    "var(--alert-danger-border)",
      border:    "var(--alert-danger-border)",
      stripe:    "var(--alert-danger-stripe)",
      labelBg:   "var(--alert-danger-label)",
      textColor: "var(--alert-danger-text)",
      divider:   "rgba(255,57,57,0.12)",
      badgeBg:   "#c62828",
      badgeText: "#fff",
      badge:     "DANGER",
    }
  : {
      topBar:    "var(--alert-warn-border)",
      border:    "var(--alert-warn-border)",
      stripe:    "var(--alert-danger-stripe)",
      labelBg:   "var(--alert-warn-label)",
      textColor: "var(--alert-warn-text)",
      divider:   "rgba(200,160,0,0.12)",
      badgeBg:   "#e65100",
      badgeText: "#fff",
      badge:     "CAUTION",
    };

/* ─── Shared card ──────────────────────────────────────────────────── */
const FieldLabel = ({ children }) => (
  <div style={{
    fontFamily:    "JetBrains Mono, monospace",
    fontSize:      "0.58rem", fontWeight: 700,
    color:         "var(--field-label-color)",
    textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: "5px",
  }}>{children}</div>
);

/* ─── Page btn ─────────────────────────────────────────────────────── */
const PageBtn = ({ disabled, onClick, children }) => (
  <button disabled={disabled} onClick={onClick} style={{
    padding: "6px 16px", borderRadius: "7px",
    border: "1px solid var(--border-normal)", background: "transparent",
    fontFamily: "JetBrains Mono, monospace", fontSize: "0.7rem", fontWeight: 600,
    letterSpacing: "0.08em",
    color: disabled ? "var(--text-muted)" : "var(--text-accent)",
    cursor: disabled ? "default" : "pointer", transition: "all 0.18s",
  }}>{children}</button>
);

/* ─── Alerts page ──────────────────────────────────────────────────── */
const Alerts = () => {
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [page,    setPage]    = useState(1);
  const [total,   setTotal]   = useState(0);
  const PAGE_SIZE  = 10;
  const requestRef = useRef(0);
  const mountedRef = useRef(true);

  const fetchAlerts = useCallback(async () => {
    const rid = ++requestRef.current;
    try {
      const res = await getAlerts({ page, page_size: PAGE_SIZE, acknowledged: false });
      if (!mountedRef.current || rid !== requestRef.current) return;
      setAlerts(res.data.alerts);
      setTotal(res.data.total);
    } catch (_) {
    } finally {
      if (mountedRef.current && rid === requestRef.current) setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    mountedRef.current = true;
    fetchAlerts();
    const t = setInterval(fetchAlerts, 5000);
    return () => { mountedRef.current = false; requestRef.current++; clearInterval(t); };
  }, [fetchAlerts]);

  const handleAck = async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      setAlerts(prev => prev.filter(a => a.alert_id !== alertId));
      setTotal(t => Math.max(0, t - 1));
    } catch (err) { console.error("Acknowledge failed", err); }
  };

  return (
    <div>
      {/* ── Header ── */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-heading)", marginBottom: "3px" }}>
          Alerts
        </h1>
        <p style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.09em",
        }}>
          {total > 0
            ? `${total} UNACKNOWLEDGED ALERT${total > 1 ? "S" : ""} · SENSOR THRESHOLD EXCEEDED`
            : "REAL-TIME HAZARD MONITORING · THRESHOLD DETECTION"}
        </p>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div style={{
          textAlign: "center", padding: "60px",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.75rem", color: "var(--text-muted)", letterSpacing: "0.14em",
        }}>
          SCANNING HAZARD CONDITIONS...
        </div>
      )}

      {/* ── No alerts ── */}
      {!loading && alerts.length === 0 && (
        <div className="lab-card" style={{ padding: "72px 48px", textAlign: "center" }}>
          <div style={{
            width: "52px", height: "52px",
            borderRadius: "50%",
            background:   "var(--nav-badge-bg)",
            border:       "1px solid var(--nav-badge-border)",
            display:      "flex", alignItems: "center", justifyContent: "center",
            margin:       "0 auto 16px",
            fontSize:     "1.5rem",
          }}>✓</div>
          <div style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "0.82rem", fontWeight: 700,
            color: "var(--text-accent)", letterSpacing: "0.14em",
            marginBottom: "10px",
          }}>
            ALL CLEAR · NO ACTIVE ALERTS
          </div>
          <div style={{
            fontFamily:    "JetBrains Mono, monospace",
            fontSize:      "0.68rem",
            color:         "var(--text-muted)",
            letterSpacing: "0.05em",
            lineHeight:    1.7,
          }}>
            System is monitoring sensor readings.<br />
            Alerts appear here when a configured threshold is exceeded.
          </div>
        </div>
      )}

      {/* ── Alert cards ── */}
      {!loading && alerts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {alerts.map(alert => {
            const t    = riskTokens(alert.risk_level);
            const icon = GAS_ICONS[alert.gas_name] ?? GAS_ICONS.default;
            return (
              <div key={alert.alert_id} style={{
                borderRadius: "12px",
                border:       `1px solid ${t.border}`,
                overflow:     "hidden",
                background:   "var(--bg-surface)",
                boxShadow:    alert.risk_level === "RED"
                  ? "0 0 20px rgba(198,40,40,0.25)"
                  : "0 0 14px rgba(200,130,0,0.15)",
              }}>
                {/* Accent top bar */}
                <div style={{ height: "3px", background: t.topBar }} />

                {/* Header */}
                <div style={{
                  padding:        "14px 20px",
                  display:        "flex",
                  justifyContent: "space-between",
                  alignItems:     "center",
                  background:     t.stripe,
                  borderBottom:   `1px solid ${t.divider}`,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                      width: "38px", height: "38px",
                      borderRadius: "8px",
                      background:   t.labelBg,
                      display:      "flex", alignItems: "center", justifyContent: "center",
                      fontSize:     "1.3rem",
                    }}>{icon}</div>
                    <div>
                      <div style={{
                        fontFamily:    "JetBrains Mono, monospace",
                        fontSize:      "0.8rem",
                        fontWeight:    700,
                        color:         "var(--text-primary)",
                        letterSpacing: "0.03em",
                      }}>
                        {alert.unit === "ADC"
                          ? `${alert.gas_name} — RAW ADC THRESHOLD EXCEEDED`
                          : `${alert.gas_name} — ABOVE CONFIGURED LIMIT`}
                      </div>
                      <div style={{
                        fontFamily:    "JetBrains Mono, monospace",
                        fontSize:      "0.63rem",
                        color:         "var(--text-muted)",
                        letterSpacing: "0.06em",
                        marginTop:     "2px",
                      }}>
                        {new Date(alert.timestamp).toLocaleString()} · {alert.device_id}
                      </div>
                    </div>
                  </div>
                  <span style={{
                    fontFamily:    "JetBrains Mono, monospace",
                    fontSize:      "0.63rem", fontWeight: 700,
                    padding:       "4px 12px", borderRadius: "4px",
                    background:    t.badgeBg, color: t.badgeText,
                    letterSpacing: "0.12em", flexShrink: 0,
                  }}>{t.badge}</span>
                </div>

                {/* Metrics row */}
                <div style={{
                  padding:             "14px 20px",
                  display:             "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap:                 "16px",
                  borderBottom:        `1px solid ${t.divider}`,
                }}>
                  {[
                    { lbl: "MEASURED",
                      val: `${(alert.measured_value ?? alert.ppm_value)?.toFixed(2)} ${alert.unit}` },
                    { lbl: alert.unit === "ADC" ? "THRESHOLD" : "WHO LIMIT",
                      val: `${alert.threshold ?? alert.who_limit} ${alert.unit}` },
                    { lbl: "EXCEEDED BY", val: `${alert.exceeded_by_pct?.toFixed(1)}%` },
                  ].map(({ lbl, val }) => (
                    <div key={lbl}>
                      <FieldLabel>{lbl}</FieldLabel>
                      <div style={{
                        fontFamily:    "JetBrains Mono, monospace",
                        fontSize:      "1.15rem",
                        fontWeight:    700,
                        color:         t.textColor,
                      }}>{val}</div>
                    </div>
                  ))}
                </div>

                {/* Health risks + actions */}
                {(alert.health_risks?.length > 0 || alert.safety_actions?.length > 0) && (
                  <div style={{
                    padding:             "14px 20px",
                    display:             "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap:                 "16px",
                    borderBottom:        `1px solid ${t.divider}`,
                  }}>
                    {alert.health_risks?.length > 0 && (
                      <div>
                        <FieldLabel>HEALTH RISKS</FieldLabel>
                        <ul style={{ paddingLeft: "14px", margin: 0 }}>
                          {alert.health_risks.slice(0, 3).map((r, i) => (
                            <li key={i} style={{
                              fontFamily: "Space Grotesk, sans-serif",
                              fontSize: "0.8rem", color: "var(--text-secondary)",
                              marginBottom: "3px",
                            }}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {alert.safety_actions?.length > 0 && (
                      <div>
                        <FieldLabel>SAFETY ACTIONS</FieldLabel>
                        <ul style={{ paddingLeft: "14px", margin: 0 }}>
                          {alert.safety_actions.slice(0, 3).map((a, i) => (
                            <li key={i} style={{
                              fontFamily: "Space Grotesk, sans-serif",
                              fontSize: "0.8rem", color: "var(--text-secondary)",
                              marginBottom: "3px",
                            }}>{a}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Footer / Acknowledge */}
                <div style={{ padding: "11px 20px", display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={() => handleAck(alert.alert_id)}
                    style={{
                      padding:       "7px 20px", borderRadius: "7px",
                      border:        `1px solid ${t.border}44`,
                      background:    t.labelBg,
                      fontFamily:    "JetBrains Mono, monospace",
                      fontSize:      "0.7rem", fontWeight: 700,
                      color:         t.textColor, cursor: "pointer",
                      letterSpacing: "0.1em", transition: "all 0.18s",
                    }}
                  >✓ ACKNOWLEDGE</button>
                </div>
              </div>
            );
          })}

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div style={{
              display: "flex", justifyContent: "center",
              gap: "10px", marginTop: "6px", alignItems: "center",
            }}>
              <PageBtn disabled={page === 1} onClick={() => setPage(p => p - 1)}>← PREV</PageBtn>
              <span style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: "0.68rem", color: "var(--text-muted)", letterSpacing: "0.08em",
              }}>
                {page} / {Math.ceil(total / PAGE_SIZE)}
              </span>
              <PageBtn disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>NEXT →</PageBtn>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Alerts;
