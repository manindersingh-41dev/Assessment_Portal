/**
 * Global Notification / Toast Store (Zustand)
 * Manages toast notifications with auto-dismissal and manual dismissal.
 */

import { create } from 'zustand';

let notificationCounter = 0;

export const useNotificationStore = create((set, get) => ({
  notifications: [],

  /**
   * Add a notification
   * @param {string} message - Toast text
   * @param {'info' | 'success' | 'warning' | 'error'} type - Category
   * @param {number} duration - Auto dismiss timeout in ms (0 = permanent)
   * @returns {number} notification id
   */
  addNotification: (message, type = 'info', duration = 4000) => {
    const id = ++notificationCounter;
    const notification = { id, message, type };

    set((state) => ({
      notifications: [...state.notifications, notification],
    }));

    if (duration > 0) {
      setTimeout(() => {
        get().removeNotification(id);
      }, duration);
    }

    return id;
  },

  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  success: (message, duration = 4000) => {
    return get().addNotification(message, 'success', duration);
  },

  error: (message, duration = 5000) => {
    return get().addNotification(message, 'error', duration);
  },

  warning: (message, duration = 4000) => {
    return get().addNotification(message, 'warning', duration);
  },

  info: (message, duration = 4000) => {
    return get().addNotification(message, 'info', duration);
  },

  clear: () => {
    set({ notifications: [] });
  },
}));

// Backward-compatible alias for non-hook call sites
export const notificationStore = useNotificationStore;

export default useNotificationStore;
