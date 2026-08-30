// ═══════════════════════════════════════════════════════
// Component 3 — Toast notifications
// Lightweight, self-contained (no external state lib) — a screen owns an
// array of toasts and renders <ToastStack/>. Matches the botanical theme.
// ═══════════════════════════════════════════════════════
import React, { useEffect } from "react";
import { F, G, GB } from "../theme";

const KIND = {
  success: { icon: "✅", color: G,          bg: GB, border: "#9ADDBB" },
  error:   { icon: "🚨", color: "#B71C1C", bg: "#FFEBEE", border: "#EF9A9A" },
  info:    { icon: "ℹ️", color: G,         bg: GB, border: "#9ADDBB" },
};

export function useToasts() {
  const [toasts, setToasts] = React.useState([]);
  const push = (message, kind = "info", duration = 4000) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts(t => [...t, { id, message, kind, duration }]);
  };
  const dismiss = (id) => setToasts(t => t.filter(x => x.id !== id));
  return { toasts, push, dismiss };
}

export default function ToastStack({ toasts, onDismiss }) {
  return (
    <div style={{ position: "fixed", top: 20, right: 20, zIndex: 2000, display: "flex", flexDirection: "column", gap: 10, maxWidth: 360 }}>
      {toasts.map(t => <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />)}
    </div>
  );
}

function ToastItem({ toast, onDismiss }) {
  const k = KIND[toast.kind] || KIND.info;
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  return (
    <div className="fade-up" style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "13px 16px", borderRadius: 10,
      background: k.bg, border: `1px solid ${k.border}`,
      boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
    }}>
      <span style={{ fontSize: 16 }}>{k.icon}</span>
      <span style={{ flex: 1, fontSize: 13, color: k.color, fontFamily: F, fontWeight: 600, lineHeight: 1.4 }}>{toast.message}</span>
      <button onClick={() => onDismiss(toast.id)}
        style={{ background: "none", border: "none", color: k.color, cursor: "pointer", fontSize: 14, opacity: 0.7, padding: 0 }}>✕</button>
    </div>
  );
}
