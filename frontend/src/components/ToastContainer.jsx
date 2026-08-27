import React from 'react';
import { TrendingUp, Info, AlertTriangle, X } from 'lucide-react';
import { useNotifications } from '../context/NotificationContext.jsx';

const ICONS = { alert: TrendingUp, warning: AlertTriangle, info: Info };

export default function ToastContainer() {
  const { toasts, dismiss } = useNotifications();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-stack" role="region" aria-label="Notifications">
      {toasts.map((t) => {
        const Icon = ICONS[t.tone] || Info;
        return (
          <div key={t.id} className={`toast toast-${t.tone}`} role="status">
            <Icon size={20} />
            <div className="toast-body">
              {t.title && <div className="toast-title">{t.title}</div>}
              {t.message && <div className="toast-message">{t.message}</div>}
            </div>
            <button
              type="button"
              className="toast-close"
              aria-label="Dismiss"
              onClick={() => dismiss(t.id)}
            >
              <X size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
