// ═══════════════════════════════════════════════════════
// Component 3 — Shared chart primitives
// Extracted from Dashboard.jsx so Reports (and anything else) can reuse the
// exact same visual language instead of duplicating SVG code. Behavior is
// unchanged from the originals.
// ═══════════════════════════════════════════════════════
import React, { useState, useEffect } from "react";
import { F, GL } from "../theme";

export function Donut({ pct, color, size = 110, label }) {
  const r = 40, cx = size / 2, cy = size / 2, circ = 2 * Math.PI * r;
  const dash = circ * Math.min(pct / 100, 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#EEEEEE" strokeWidth={9} />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={9}
          strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={circ * 0.25}
          strokeLinecap="round" style={{ transition: "stroke-dasharray 1.2s ease" }} />
        <text x={cx} y={cy - 4} textAnchor="middle" style={{ fontSize: 15, fontWeight: 700, fill: color, fontFamily: F }}>{Math.round(pct)}%</text>
        <text x={cx} y={cy + 13} textAnchor="middle" style={{ fontSize: 9, fill: "#9E9E9E", fontFamily: F }}>of max</text>
      </svg>
      <div style={{ fontSize: 11, color: "#757575", fontFamily: F, textAlign: "center" }}>{label}</div>
    </div>
  );
}

export function BarChart({ data, height = 140 }) {
  const maxVal = Math.max(...data.map(d => d.value), 1);
  const barW = 36, gap = 14, total = data.length * (barW + gap) - gap;
  return (
    <svg width={total + 40} height={height + 40} style={{ overflow: "visible" }}>
      {[0, 25, 50, 75, 100].map(g => {
        const y = 10 + height - (g / 100) * height;
        return <g key={g}>
          <line x1={20} y1={y} x2={total + 20} y2={y} stroke="#F0F0F0" strokeWidth={1} />
          <text x={16} y={y + 4} textAnchor="end" style={{ fontSize: 8, fill: "#BDBDBD", fontFamily: F }}>{g}%</text>
        </g>;
      })}
      {data.map((d, i) => {
        const x = 20 + i * (barW + gap), barH = (d.value / maxVal) * height, y = 10 + height - barH;
        return <g key={i}>
          <rect x={x} y={y} width={barW} height={barH} rx={4} fill={d.color} opacity={0.85} />
          <text x={x + barW / 2} y={y - 5} textAnchor="middle" style={{ fontSize: 9, fontWeight: 700, fill: d.color, fontFamily: F }}>{d.display}</text>
          <text x={x + barW / 2} y={height + 26} textAnchor="middle" style={{ fontSize: 9, fill: "#757575", fontFamily: F }}>{d.label}</text>
        </g>;
      })}
    </svg>
  );
}

export function HBar({ value, max, color, label, unit, delay = 0 }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW((value / max) * 100), delay + 120); return () => clearTimeout(t); }, [value, max, delay]);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "#555", fontFamily: F }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: F }}>{value}{unit}</span>
      </div>
      <div style={{ height: 8, background: "#EEEEEE", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${w}%`, background: color, borderRadius: 4, transition: "width 1.3s ease" }} />
      </div>
    </div>
  );
}

export function Radar({ data, size = 180, color = GL }) {
  const cx = size / 2, cy = size / 2, r = size * 0.36, n = data.length;
  const ang = (i) => (Math.PI * 2 * i / n) - Math.PI / 2;
  const pt = (i, v) => ({ x: cx + r * Math.cos(ang(i)) * v, y: cy + r * Math.sin(ang(i)) * v });
  const gridPts = (v) => data.map((_, i) => pt(i, v));
  return (
    <svg width={size} height={size}>
      {[0.25, 0.5, 0.75, 1].map(v => (
        <polygon key={v} points={gridPts(v).map(p => `${p.x},${p.y}`).join(" ")} fill="none" stroke="#E8E8E8" strokeWidth={0.8} />
      ))}
      {data.map((_, i) => { const e = pt(i, 1); return <line key={i} x1={cx} y1={cy} x2={e.x} y2={e.y} stroke="#E8E8E8" strokeWidth={0.8} />; })}
      <polygon points={data.map((d, i) => { const p = pt(i, d.value); return `${p.x},${p.y}`; }).join(" ")}
        fill="rgba(46,125,50,0.15)" stroke={color} strokeWidth={2} />
      {data.map((d, i) => {
        const p = pt(i, d.value), lp = pt(i, 1.22);
        return <g key={i}>
          <circle cx={p.x} cy={p.y} r={4} fill={color} />
          <text x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle"
            style={{ fontSize: 9, fill: "#555", fontFamily: F }}>{d.label}</text>
        </g>;
      })}
    </svg>
  );
}
