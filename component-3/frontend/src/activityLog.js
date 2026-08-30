// ═══════════════════════════════════════════════════════
// Component 3 — Real session activity log
// This app has no accounts/backend notification store, so rather than
// fabricate a fake notification inbox, this tracks what actually happened
// in this browser session (optimize runs, batches, detections, reports).
// Module-level store + subscriber list, kept simple on purpose — no Redux/
// Context needed for a handful of subscribers.
// ═══════════════════════════════════════════════════════
import { useState, useEffect } from "react";

let log = [];
let listeners = [];

function emit() { listeners.forEach(fn => fn(log)); }

export function logActivity(type, message) {
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    type, message, timestamp: new Date().toISOString(), read: false,
  };
  log = [entry, ...log].slice(0, 50);
  emit();
}

export function markAllRead() {
  log = log.map(e => ({ ...e, read: true }));
  emit();
}

export function markRead(id) {
  log = log.map(e => e.id === id ? { ...e, read: true } : e);
  emit();
}

export function useActivityLog() {
  const [entries, setEntries] = useState(log);
  useEffect(() => {
    listeners.push(setEntries);
    return () => { listeners = listeners.filter(l => l !== setEntries); };
  }, []);
  return entries;
}
