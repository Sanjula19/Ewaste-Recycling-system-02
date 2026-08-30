// ═══════════════════════════════════════════════════════
// Component 3 — Confirmation dialog
// Small centered modal for destructive actions (e.g. deleting a report).
// ═══════════════════════════════════════════════════════
import React from "react";
import { F, G, GL } from "../theme";

export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", danger = false, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div onClick={onCancel} style={{
      position: "fixed", inset: 0, background: "rgba(23,107,77,0.25)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 3000,
    }}>
      <div onClick={e => e.stopPropagation()} className="fade-up" style={{
        background: "#FFFFFF", borderRadius: 12, padding: "26px 28px", width: 380, maxWidth: "90vw",
        boxShadow: "0 12px 40px rgba(0,0,0,0.2)", border: "1px solid #E0E0E0",
      }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: danger ? "#B71C1C" : G, fontFamily: F, marginBottom: 10 }}>{title}</div>
        <div style={{ fontSize: 13, color: "#555", fontFamily: F, lineHeight: 1.5, marginBottom: 22 }}>{message}</div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button onClick={onCancel} style={{
            padding: "9px 18px", borderRadius: 8, border: "1px solid #E0E0E0", background: "#FAFAFA",
            color: "#555", fontFamily: F, fontSize: 13, fontWeight: 600, cursor: "pointer",
          }}>{cancelLabel}</button>
          <button onClick={onConfirm} style={{
            padding: "9px 18px", borderRadius: 8, border: "none",
            background: danger ? "#B71C1C" : `linear-gradient(135deg,${GL},${G})`,
            color: "#FFFFFF", fontFamily: F, fontSize: 13, fontWeight: 700, cursor: "pointer",
          }}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
