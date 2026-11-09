/**
 * Authentication API service for account lifecycle and session operations.
 */

import api from './client.js';
import { config } from '../constants/config.js';

const getTokenClaims = () => {
  try {
    const token = localStorage.getItem(config.auth.tokenKey);
    const payload = token?.split('.')[1];
    if (!payload) return {};

    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(window.atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')));
  } catch {
    return {};
  }
};

const getUserId = (userId) => userId || getTokenClaims().user_id || getTokenClaims().userId;
const profileBase = config.api.endpoints.auth.profile;
const profileUrl = (userId) => `${profileBase.replace(/\/$/, '')}/${encodeURIComponent(userId)}/`;

export const normalizeAuthUser = (user = {}) => {
  const fullName = user.full_name || user.name || [user.first_name, user.last_name].filter(Boolean).join(' ');
  const nameParts = fullName.trim().split(/\s+/).filter(Boolean);

  return {
    ...user,
    full_name: fullName,
    first_name: user.first_name || nameParts[0] || '',
    last_name: user.last_name || nameParts.slice(1).join(' '),
  };
};

export const getAuthErrorMessage = (error, fallback = 'Something went wrong. Please try again.') => {
  const data = error?.response?.data;
  const preferred = data?.details || data?.errors || data?.detail || data?.error || data?.message || data;

  const collectMessages = (value, field = '') => {
    if (typeof value === 'string' && value.trim()) {
      const prefix = field && field !== 'non_field_errors' ? `${field.replaceAll('_', ' ')}: ` : '';
      return [`${prefix}${value.trim()}`];
    }
    if (Array.isArray(value)) {
      return value.flatMap((item) => collectMessages(item, field));
    }
    if (value && typeof value === 'object') {
      return Object.entries(value).flatMap(([key, item]) => collectMessages(item, key));
    }
    return [];
  };

  const messages = [...new Set(collectMessages(preferred))];
  return messages.join(' ') || error?.message || fallback;
};

const authService = {
  login: async (email, password) => {
    const response = await api.post(config.api.endpoints.auth.login, {
      email: email.trim().toLowerCase(),
      password,
    });
    const data = response.data;

    return {
      ...data,
      access: data.access || data.tokens?.access,
      refresh: data.refresh || data.tokens?.refresh,
      user: data.user ? normalizeAuthUser(data.user) : null,
    };
  },

  registerStudent: async (userData) => {
    const payload = {
      email: userData.email.trim().toLowerCase(),
      password: userData.password,
      password_confirm: userData.password_confirm || userData.password,
      roll_number: userData.roll_number?.trim(),
      department: userData.department?.trim(),
      year_of_study: Number.parseInt(userData.year_of_study, 10),
      first_name: userData.first_name?.trim() || '',
      last_name: userData.last_name?.trim() || '',
    };
    const response = await api.post(config.api.endpoints.auth.registerStudent, payload);
    return response.data;
  },

  registerFaculty: async (userData) => {
    const payload = {
      email: userData.email.trim().toLowerCase(),
      password: userData.password,
      password_confirm: userData.password_confirm || userData.password,
      employee_id: userData.employee_id?.trim(),
      department: userData.department?.trim(),
      designation: userData.designation?.trim(),
      first_name: userData.first_name?.trim() || '',
      last_name: userData.last_name?.trim() || '',
    };
    const response = await api.post(config.api.endpoints.auth.registerFaculty, payload);
    return response.data;
  },

  verifyEmail: async (email, otp, loginChallenge = null) => {
    const payload = { email, otp };
    if (loginChallenge) payload.login_challenge = loginChallenge;
    const response = await api.post(config.api.endpoints.auth.verifyEmail, payload);
    return response.data;
  },

  resendOTP: async (email, purpose = 'email_verification') => {
    const response = await api.post(config.api.endpoints.auth.resendOtp, { email, purpose });
    return response.data;
  },

  forgotPassword: async (email) => {
    const response = await api.post(config.api.endpoints.auth.passwordResetRequest, {
      email: email.trim().toLowerCase(),
    });
    return response.data;
  },

  resetPassword: async ({ email, otp, new_password, new_password_confirm }) => {
    const response = await api.post(config.api.endpoints.auth.passwordReset, {
      email: email.trim().toLowerCase(),
      otp,
      new_password,
      new_password_confirm: new_password_confirm || new_password,
    });
    return response.data;
  },

  refreshToken: async (refresh) => {
    const response = await api.post(config.api.endpoints.auth.refresh, { refresh });
    return response.data;
  },

  getProfile: async (userId) => {
    const resolvedUserId = getUserId(userId);

    // The current Django router exposes ProfileView as a detail route. Keep the
    // documented collection URL as a fallback for deployments that expose it.
    if (resolvedUserId) {
      try {
        const response = await api.get(profileUrl(resolvedUserId));
        return normalizeAuthUser(response.data);
      } catch (error) {
        if (![404, 405].includes(error.response?.status)) throw error;
      }
    }

    const response = await api.get(profileBase);
    return normalizeAuthUser(response.data);
  },

  updateProfile: async (userData, userId) => {
    const resolvedUserId = getUserId(userId);
    const url = resolvedUserId ? profileUrl(resolvedUserId) : profileBase;
    const response = await api.patch(url, userData);
    return response.data;
  },

  logout: async (refreshToken, accessToken) => {
    const response = await api.post(
      config.api.endpoints.auth.logout,
      { refresh_token: refreshToken },
      accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : undefined
    );
    return response.data;
  },
};

export default authService;
