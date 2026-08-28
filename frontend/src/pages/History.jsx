import React, { useState, useEffect, useCallback } from "react";
import { getReadings, getChartData } from "../services/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const PAGE_SIZE = 20;

/* ─── Card ─────────────────────────────────────────────────────────── */
const Card = ({ children, style = {} }) => (
  <div className="lab-card" style={style}>{children}</div>
);

/* ─── Custom chart tooltip ─────────────────────────────────────────── */
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background:   "var(--bg-surface-2)",
      border:       "1px solid var(--border-normal)",
      borderRadius: "8px",
      padding:      "10px 14px",
      boxShadow:    "var(--shadow-card)",
    }}>
      <div style={{
        fontFamily:    "JetBrains Mono, monospace",
        fontSize:      "0.63rem",
        color:         "var(--text-muted)",
        letterSpacing: "0.1em",
        marginBottom:  "8px",
      }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{
          fontFamily:     "JetBrains Mono, monospace",
          fontSize:       "0.75rem",
          color:          p.color,
          display:        "flex",
          justifyContent: "space-between",
          gap:            "16px",
          marginBottom:   "3px",
        }}>
          <span style={{ color: "var(--text-secondary)" }}>{p.name}</span>
          <span style={{ fontWeight: 700, color: p.color }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
};

/* ─── Btn helper ────────────────────────────────────────────────────── */
const PageBtn = ({ disabled, onClick, children }) => (
  <button
    disabled={disabled}
    onClick={onClick}
    style={{
      padding:       "6px 16px",
      borderRadius:  "7px",
      border:        "1px solid var(--border-normal)",
      background:    "transparent",
      fontFamily:    "JetBrains Mono, monospace",
      fontSize:      "0.7rem",
      fontWeight:    600,
      letterSpacing: "0.08em",
      color:         disabled ? "var(--text-muted)" : "var(--text-accent)",
      cursor:        disabled ? "default" : "pointer",
      transition:    "all 0.18s",
    }}
  >{children}</button>
);

/* ─── History page ─────────────────────────────────────────────────── */
const History = () => {
  const [rows,    setRows]    = useState([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [chart,   setChart]   = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTable = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getReadings({ page, page_size: PAGE_SIZE });
      setRows(res.data.readings);
      setTotal(res.data.total);
    } catch (_) { setRows([]); }
    setLoading(false);
  }, [page]);

  const fetchChart = useCallback(async () => {
    try {
      const res = await getChartData({ limit: 40 });
      setChart(res.data.data_points.map(p => ({
        time:    new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        "MQ-2":  p.mq2_raw   ?? null,
        "MQ-7":  p.mq7_raw   ?? null,
        "MQ-135":p.mq135_raw ?? null,
        "Temp":  p.temperature_c != null ? parseFloat(p.temperature_c.toFixed(1)) : null,
      })));
    } catch (_) {}
  }, []);

  useEffect(() => { fetchTable(); }, [fetchTable]);
  useEffect(() => { fetchChart(); }, [fetchChart]);

  const exportCSV = () => {
    if (!rows.length) return;
    const hdr  = ["Timestamp","Device ID","MQ-2 ADC","MQ-7 ADC","MQ-135 ADC","Temp (C)","Humidity (%)"];
    const body = rows.map(r => [
      new Date(r.received_at).toLocaleString(),
      r.device_id,
      r.mq2_raw   ?? "",
      r.mq7_raw   ?? "",
      r.mq135_raw ?? "",
      r.temperature_c != null ? r.temperature_c.toFixed(1) : "",
      r.humidity_pct  != null ? r.humidity_pct.toFixed(1)  : "",
    ].join(","));
    const blob = new Blob([[hdr.join(","), ...body].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ewaste_readings_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  /* Column definitions */
  const columns = [
    { key: "received_at",   label: "TIMESTAMP",   valColor: "var(--text-secondary)" },
    { key: "device_id",     label: "DEVICE",      valColor: "var(--text-muted)"     },
    { key: "mq2_raw",       label: "MQ-2 ADC",    valColor: "var(--val-mq2)"        },
    { key: "mq7_raw",       label: "MQ-7 ADC",    valColor: "var(--val-mq7)"        },
    { key: "mq135_raw",     label: "MQ-135 ADC",  valColor: "var(--val-mq135)"      },
    { key: "temperature_c", label: "TEMP (°C)",   valColor: "var(--val-temp)"       },
    { key: "humidity_pct",  label: "HUM (%)",     valColor: "var(--val-hum)"        },
  ];

  const renderCell = (r, col) => {
    switch (col.key) {
      case "received_at":    return new Date(r.received_at).toLocaleString();
      case "device_id":      return r.device_id;
      case "mq2_raw":        return r.mq2_raw   ?? null;
      case "mq7_raw":        return r.mq7_raw    ?? null;
      case "mq135_raw":      return r.mq135_raw  ?? null;
      case "temperature_c":  return r.temperature_c != null ? r.temperature_c.toFixed(1) : null;
      case "humidity_pct":   return r.humidity_pct  != null ? r.humidity_pct.toFixed(1)  : null;
      default:               return null;
    }
  };

  return (
    <div>
      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text-heading)", marginBottom: "3px" }}>
            History
          </h1>
          <p style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.09em",
          }}>
            {total > 0
              ? `${total.toLocaleString()} READINGS STORED · SQLITE · REAL SENSOR DATA`
              : "AWAITING SENSOR DATA"}
          </p>
        </div>
        {rows.length > 0 && (
          <button onClick={exportCSV} style={{
            padding:       "8px 18px",
            borderRadius:  "8px",
            border:        "1px solid var(--border-accent)",
            background:    "var(--nav-badge-bg)",
            fontFamily:    "JetBrains Mono, monospace",
            fontSize:      "0.72rem",
            fontWeight:    600,
            letterSpacing: "0.08em",
            color:         "var(--text-accent)",
            cursor:        "pointer",
            transition:    "all 0.2s",
          }}>⬇ EXPORT CSV</button>
        )}
      </div>

      {/* ── Trend chart ── */}
      {chart.length > 2 && (
        <Card style={{ padding: "18px 22px", marginBottom: "14px" }}>
          <div style={{
            fontFamily:    "JetBrains Mono, monospace",
            fontSize:      "0.62rem",
            fontWeight:    700,
            color:         "var(--section-label-color)",
            letterSpacing: "0.14em",
            marginBottom:  "16px",
          }}>
            SENSOR TREND · LAST {chart.length} READINGS
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis
                dataKey="time"
                tick={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, fill: "var(--text-muted)" }}
                axisLine={{ stroke: "var(--chart-axis)" }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, fill: "var(--text-muted)" }}
                axisLine={{ stroke: "var(--chart-axis)" }}
                tickLine={false}
                width={40}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem" }} />
              <Line type="monotone" dataKey="MQ-2"  stroke="var(--val-mq2)"   strokeWidth={1.8} dot={false} connectNulls />
              <Line type="monotone" dataKey="MQ-7"  stroke="var(--val-mq7)"   strokeWidth={1.8} dot={false} connectNulls />
              <Line type="monotone" dataKey="MQ-135" stroke="var(--val-mq135)" strokeWidth={1.8} dot={false} connectNulls />
              <Line type="monotone" dataKey="Temp"  stroke="var(--val-temp)"  strokeWidth={1.5} dot={false} connectNulls strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* ── Table ── */}
      <Card>
        {loading ? (
          <div style={{
            padding:    "56px",
            textAlign:  "center",
            fontFamily: "JetBrains Mono, monospace",
            fontSize:   "0.75rem",
            color:      "var(--text-muted)",
            letterSpacing: "0.14em",
          }}>
            LOADING SENSOR DATA...
          </div>
        ) : rows.length === 0 ? (
          <div style={{ padding: "64px", textAlign: "center" }}>
            <div style={{ fontSize: "2.4rem", marginBottom: "14px", opacity: 0.35 }}>📋</div>
            <div style={{
              fontFamily:    "JetBrains Mono, monospace",
              fontSize:      "0.78rem",
              color:         "var(--text-muted)",
              letterSpacing: "0.1em",
            }}>NO READINGS STORED · CONNECT ESP32 TO BEGIN DATA COLLECTION</div>
          </div>
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    {columns.map(col => (
                      <th key={col.key} style={{
                        padding:       "12px 14px",
                        textAlign:     "left",
                        fontFamily:    "JetBrains Mono, monospace",
                        fontSize:      "0.6rem",
                        fontWeight:    700,
                        textTransform: "uppercase",
                        letterSpacing: "0.12em",
                        color:         col.valColor,
                        background:    "var(--table-header-bg)",
                        whiteSpace:    "nowrap",
                      }}>
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={r.reading_id || i} style={{
                      borderBottom: "1px solid var(--table-divider)",
                      background:   i % 2 === 0 ? "var(--table-row-a)" : "var(--table-row-b)",
                    }}>
                      {columns.map((col, ci) => {
                        const val = renderCell(r, col);
                        const isId  = col.key === "received_at" || col.key === "device_id";
                        const isNum = !isId;
                        return (
                          <td key={col.key} style={{
                            padding:     "10px 14px",
                            fontFamily:  "JetBrains Mono, monospace",
                            fontSize:    isNum ? "0.88rem" : "0.73rem",
                            fontWeight:  isNum ? 700 : 400,
                            color:       val != null ? col.valColor : "var(--border-subtle)",
                            whiteSpace:  ci === 0 ? "nowrap" : undefined,
                          }}>
                            {val ?? "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{
                padding:       "12px 16px",
                borderTop:     "1px solid var(--border-divider)",
                display:       "flex",
                justifyContent:"center",
                alignItems:    "center",
                gap:           "12px",
              }}>
                <PageBtn disabled={page === 1} onClick={() => setPage(p => p - 1)}>← PREV</PageBtn>
                <span style={{
                  fontFamily:    "JetBrains Mono, monospace",
                  fontSize:      "0.68rem",
                  color:         "var(--text-muted)",
                  letterSpacing: "0.08em",
                }}>
                  {page} / {totalPages}
                </span>
                <PageBtn disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>NEXT →</PageBtn>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
};

export default History;
