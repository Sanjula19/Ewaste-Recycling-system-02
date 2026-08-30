// ═══════════════════════════════════════════════════════
// Component 3 — Notification bell
// Shows real session activity (see activityLog.js) — not fabricated data.
// Closes on outside click / Escape, keyboard-focusable.
// ═══════════════════════════════════════════════════════
import React, { useState, useRef, useEffect } from "react";
import { F, G, GL, GLL, GB } from "../theme";
import { useActivityLog, markAllRead, markRead } from "../activityLog";

const TYPE_META = {
  optimize:  { icon: "⚡", color: GL },
  batch:     { icon: "📦", color: "#D97706" },
  detection: { icon: "📷", color: "#16817A" },
  report:    { icon: "📄", color: "#6A1B9A" },
  "report-delete": { icon: "🗑", color: "#B71C1C" },
  sensor:    { icon: "💧", color: "#1565C0" },
};

function relTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

export default function NotificationBell({ darkMode }) {
  const entries = useActivityLog();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const unread = entries.filter(e => !e.read).length;

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDocClick); document.removeEventListener("keydown", onEsc); };
  }, [open]);

  const panelBg = darkMode ? "#17231F" : "#FFFFFF";
  const panelBorder = darkMode ? "#315348" : "#E0E0E0";
  const textCol = darkMode ? "#F0F7F3" : "#1A1A1A";
  const subCol = darkMode ? "#B8C9C1" : "#9E9E9E";

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen(o => !o)} aria-label="Notifications" title="Activity"
        style={{
          position: "relative", display: "flex", alignItems: "center", justifyContent: "center",
          width: 36, height: 36, borderRadius: 18, border: `1px solid ${darkMode ? "#477563" : GLL + "60"}`,
          background: darkMode ? "#20332B" : GB, color: darkMode ? "#F0F7F3" : G, cursor: "pointer", fontSize: 16,
        }}>
        🔔
        {unread > 0 && (
          <span style={{
            position: "absolute", top: -3, right: -3, minWidth: 16, height: 16, padding: "0 3px", borderRadius: 8,
            background: "#C62828", color: "#fff", fontSize: 9.5, fontWeight: 700, fontFamily: F,
            display: "flex", alignItems: "center", justifyContent: "center", border: "2px solid " + (darkMode ? "#101815" : "#FFFFFF"),
          }}>{unread > 9 ? "9+" : unread}</span>
        )}
      </button>

      {open && (
        <div className="fade-up" style={{
          position: "absolute", top: 44, right: 0, width: 340, maxHeight: 420, overflowY: "auto",
          background: panelBg, border: `1px solid ${panelBorder}`, borderRadius: 12,
          boxShadow: "0 12px 32px rgba(0,0,0,0.18)", zIndex: 200,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: `1px solid ${panelBorder}` }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: textCol, fontFamily: F }}>Activity</span>
            {unread > 0 && (
              <button onClick={markAllRead} style={{ background: "none", border: "none", color: GL, fontSize: 11.5, fontWeight: 700, fontFamily: F, cursor: "pointer" }}>Mark all read</button>
            )}
          </div>

          {entries.length === 0 ? (
            <div style={{ padding: "36px 20px", textAlign: "center" }}>
              <div style={{ fontSize: 28, opacity: 0.25, marginBottom: 8 }}>🔔</div>
              <div style={{ fontSize: 12, color: subCol, fontFamily: F }}>No activity yet this session</div>
            </div>
          ) : (
            entries.map(e => {
              const meta = TYPE_META[e.type] || { icon: "•", color: GL };
              return (
                <div key={e.id} onClick={() => markRead(e.id)} style={{
                  display: "flex", gap: 10, padding: "11px 16px", cursor: "pointer",
                  borderBottom: `1px solid ${panelBorder}`, background: e.read ? "transparent" : (darkMode ? "#1B2B25" : GB),
                }}>
                  <span style={{ fontSize: 15, flexShrink: 0 }}>{meta.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, color: textCol, fontFamily: F, fontWeight: e.read ? 400 : 700, lineHeight: 1.4 }}>{e.message}</div>
                    <div style={{ fontSize: 10.5, color: subCol, fontFamily: F, marginTop: 2 }}>{relTime(e.timestamp)}</div>
                  </div>
                  {!e.read && <div style={{ width: 7, height: 7, borderRadius: "50%", background: meta.color, flexShrink: 0, marginTop: 4 }} />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
