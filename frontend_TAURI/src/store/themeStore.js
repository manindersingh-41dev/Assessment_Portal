/**
 * Global Theme Store (Zustand)
 * Controls Light / Dark mode across the application and persists to localStorage.
 */

import { create } from 'zustand';

export const useThemeStore = create((set, get) => ({
  theme: localStorage.getItem('theme') || 'light',

  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme });
  },

  toggleTheme: () => {
    const currentTheme = get().theme;
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    get().setTheme(newTheme);
  },

  initializeTheme: () => {
    const theme = localStorage.getItem('theme') || 'light';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme });
  },
}));

// Backward-compatible alias
export const themeStore = useThemeStore;

export default useThemeStore;
