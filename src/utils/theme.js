/**
 * Centralized Theme Engine for Exam Jingga (Material Design 3)
 * Mencegah FOUC, ghosting, dan inkonsistensi storage key antar-halaman.
 */

export function getTheme() {
  if (typeof window === 'undefined') return 'light';
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function isDarkMode() {
  if (typeof window === 'undefined') return false;
  return document.documentElement.classList.contains('dark');
}

export function setTheme(theme) {
  if (typeof window === 'undefined') return;
  const isDark = theme === 'dark';
  
  if (isDark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  // Sinkronkan legacy key jika ada
  localStorage.theme = isDark ? 'dark' : 'light';

  // Dispatch custom event untuk sinkronisasi instan antar komponen tanpa reload
  window.dispatchEvent(new CustomEvent('exam-jingga-theme-change', { detail: { theme: isDark ? 'dark' : 'light' } }));
}

export function toggleTheme() {
  const current = isDarkMode() ? 'dark' : 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next === 'dark';
}
