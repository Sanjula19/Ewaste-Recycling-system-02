import React, { useEffect, useState } from 'react';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function LiveClock() {
  const { intlTag } = useLanguage();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const dateStr = new Intl.DateTimeFormat(intlTag, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(now);

  const timeStr = new Intl.DateTimeFormat(intlTag, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(now);

  return (
    <div className="live-clock" aria-live="off">
      <span className="live-clock-date">{dateStr}</span>
      <span className="live-clock-time">{timeStr}</span>
    </div>
  );
}
