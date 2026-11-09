/**
 * Utility Functions
 * Common helper functions
 */

/**
 * Format date to readable string
 */
export const formatDate = (date, format = 'short') => {
  const d = new Date(date);
  const options = {
    short: { year: 'numeric', month: 'short', day: 'numeric' },
    long: { year: 'numeric', month: 'long', day: 'numeric' },
    time: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' },
    datetime: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' },
  };
  return d.toLocaleDateString('en-US', options[format] || options.short);
};

/**
 * Format time difference
 */
export const formatTimeAgo = (date) => {
  const now = new Date();
  const seconds = Math.floor((now - new Date(date)) / 1000);

  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
  };

  for (const [key, value] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / value);
    if (interval >= 1) {
      return interval === 1 ? `${interval} ${key} ago` : `${interval} ${key}s ago`;
    }
  }

  return 'just now';
};

/**
 * Get verdict badge color
 */
export const getVerdictColor = (verdict) => {
  const colors = {
    accepted: 'success',
    wrong_answer: 'danger',
    compilation_error: 'warning',
    runtime_error: 'warning',
    time_limit_exceeded: 'warning',
    memory_limit_exceeded: 'warning',
    pending: 'primary',
  };
  return colors[verdict] || 'primary';
};

/**
 * Get status badge color
 */
export const getStatusColor = (status) => {
  const colors = {
    completed: 'success',
    pending: 'warning',
    failed: 'danger',
    in_progress: 'primary',
    started: 'primary',
  };
  return colors[status] || 'primary';
};

/**
 * Get role display name
 */
export const getRoleDisplay = (role) => {
  const roles = {
    faculty: 'Faculty',
    student: 'Student',
    admin: 'Administrator',
  };
  return roles[role] || role;
};

/**
 * Get difficulty badge color
 */
export const getDifficultyColor = (difficulty) => {
  const colors = {
    easy: 'success',
    medium: 'warning',
    hard: 'danger',
  };
  return colors[difficulty?.toLowerCase()] || 'primary';
};

/**
 * Truncate text
 */
export const truncate = (text, length = 100) => {
  return text.length > length ? text.substring(0, length) + '...' : text;
};

/**
 * Format bytes
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format percentage
 */
export const formatPercentage = (value, decimals = 1) => {
  return parseFloat(value).toFixed(decimals) + '%';
};

/**
 * Check if email is valid
 */
export const isValidEmail = (email) => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
};

/**
 * Check if password is strong
 */
export const isStrongPassword = (password) => {
  return (
    password.length >= 8 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /[0-9]/.test(password)
  );
};

/**
 * Debounce function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Clone object
 */
export const deepClone = (obj) => {
  return JSON.parse(JSON.stringify(obj));
};

/**
 * Get initials from name
 */
export const getInitials = (firstName, lastName = '') => {
  const first = firstName?.charAt(0)?.toUpperCase() || '';
  const last = lastName?.charAt(0)?.toUpperCase() || '';
  return (first + last) || '?';
};

/**
 * Generate random color
 */
export const getColorForRole = (role) => {
  const colors = {
    faculty: 'bg-purple-500',
    student: 'bg-blue-500',
    admin: 'bg-red-500',
  };
  return colors[role] || 'bg-slate-500';
};

/**
 * Format duration in seconds to readable string
 */
export const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0) parts.push(`${secs}s`);

  return parts.join(' ') || '0s';
};
