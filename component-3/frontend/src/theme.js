// ═══════════════════════════════════════════════════════
// Component 3 — Shared design tokens
// Single source of truth for colors/typography/status meta so every screen
// (Dashboard, Reports, …) stays visually consistent. Extracted from the
// original Dashboard.jsx botanical theme — values are unchanged.
// ═══════════════════════════════════════════════════════

export const F = "Times New Roman, Georgia, serif";

// Light botanical theme — softer/lighter sage green
export const G   = "#2F7A5C"; // sage green (primary)
export const GL  = "#4CAE84"; // fresh green (accent)
export const GLL = "#8FD4B0"; // light mint accent
export const GB  = "#F0FBF6"; // soft mint background

export const CAT_ICONS = { Paper: "📄", Plastic: "🧴", Glass: "🫙" };

export const CAT_COLORS = {
  Paper:   { main: "#4CAE84", light: "#F0FBF6", bar: "#8FD4B0" },
  Plastic: { main: "#D97706", light: "#FFF5DF", bar: "#F2A93B" },
  Glass:   { main: "#16817A", light: "#E3F6F2", bar: "#55BDB2" },
};

export const SAFETY_META = {
  CRITICAL: { color: "#C62828", light: "#FFEBEE", border: "#EF9A9A", icon: "🚨", label: "Critical Risk" },
  WARNING:  { color: "#D97706", light: "#FFF5DF", border: "#F3C878", icon: "⚠️", label: "Warning" },
  SECURE:   { color: "#2F7A5C", light: "#F0FBF6", border: "#9ADDBB", icon: "✅", label: "Secure" },
};

export const METHOD_META = {
  Mechanical: { icon: "⚙️", color: "#4CAE84", light: "#F0FBF6", desc: "Shred & Crush" },
  Thermal:    { icon: "🔥", color: "#C65D24", light: "#FFF0E7", desc: "Melt & Pyrolysis" },
  Chemical:   { icon: "🧪", color: "#4A148C", light: "#F3E5F5", desc: "Chemical Treatment" },
};

export function getSafetyMeta(status) {
  return SAFETY_META[status] || SAFETY_META.SECURE;
}

export function getMethodMeta(method) {
  if (!method) return METHOD_META.Mechanical;
  const k = Object.keys(METHOD_META).find(k => method.toLowerCase().includes(k.toLowerCase()));
  return METHOD_META[k] || METHOD_META.Mechanical;
}
