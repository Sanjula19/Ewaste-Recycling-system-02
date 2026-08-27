import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

const NotificationContext = createContext(null);

let nextId = 1;
const AUTO_DISMISS_MS = 7000;

/** Short two-tone alarm beep for a SELL NOW alert -- built with Web Audio, no external asset. */
function playAlertBeep() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const playTone = (freq, startAt, duration) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, startAt);
      gain.gain.exponentialRampToValueAtTime(0.15, startAt + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
      osc.connect(gain).connect(ctx.destination);
      osc.start(startAt);
      osc.stop(startAt + duration);
    };
    const now = ctx.currentTime;
    playTone(880, now, 0.16);
    playTone(1108, now + 0.18, 0.2);
  } catch {
    /* autoplay blocked or no audio support -- the visual toast still shows */
  }
}

export function NotificationProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    clearTimeout(timers.current[id]);
    delete timers.current[id];
  }, []);

  const notify = useCallback(({ tone = 'info', title, message }) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, tone, title, message }]);
    timers.current[id] = setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    if (tone === 'alert') playAlertBeep();
  }, [dismiss]);

  return (
    <NotificationContext.Provider value={{ toasts, notify, dismiss }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications must be used within a NotificationProvider');
  return ctx;
}
