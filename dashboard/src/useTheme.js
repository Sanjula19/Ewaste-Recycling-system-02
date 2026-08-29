import { useEffect, useState } from 'react';

const STORAGE_KEY = 'ewaste-dashboard-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE_KEY, theme);
}

export function useTheme() {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const saved =
      localStorage.getItem(STORAGE_KEY) ||
      (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    applyTheme(saved);
    setTheme(saved);
  }, []);

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    setTheme(next);
  }

  return { theme, toggle };
}
