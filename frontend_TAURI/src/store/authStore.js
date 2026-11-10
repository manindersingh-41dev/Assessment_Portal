/**
 * Session state and account lifecycle actions.
 */

import { create } from 'zustand';
import { config } from '../constants/config.js';
import authService, { getAuthErrorMessage, normalizeAuthUser } from '../api/auth.js';
import { setAuthenticationExpiredHandler } from '../api/client.js';

let initializationRequest = null;

const clearStoredTokens = () => {
  localStorage.removeItem(config.auth.tokenKey);
  localStorage.removeItem(config.auth.refreshTokenKey);
};

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  loading: true,
  error: null,

  initialize: () => {
    if (initializationRequest) return initializationRequest;

    initializationRequest = (async () => {
      set({ loading: true, error: null });
      try {
        const accessToken = localStorage.getItem(config.auth.tokenKey);
        if (!accessToken) {
          set({ user: null, isAuthenticated: false, error: null });
          return null;
        }

        const user = await authService.getProfile();
        set({ user, isAuthenticated: true, loading: false, error: null });
        return user;
      } catch {
        get().clearSession();
        return null;
      } finally {
        set({ loading: false });
        initializationRequest = null;
      }
    })();

    return initializationRequest;
  },

  login: async (email, password) => {
    set({ error: null });
    sessionStorage.removeItem('pending_login_verification_challenge');
    try {
      const data = await authService.login(email, password);
      if (data.verification_required) {
        const pendingEmail = data.email || email.trim().toLowerCase();
        sessionStorage.setItem('pending_verification_email', pendingEmail);
        sessionStorage.setItem('pending_login_verification_challenge', data.login_challenge || '');
        clearStoredTokens();
        set({ user: null, isAuthenticated: false, error: null });
        return {
          verificationRequired: true,
          email: pendingEmail,
          role: data.role,
        };
      }
      if (!data.access) throw new Error('The server did not return an access token.');

      localStorage.setItem(config.auth.tokenKey, data.access);
      if (data.refresh) localStorage.setItem(config.auth.refreshTokenKey, data.refresh);

      let user = data.user;
      if (!user) {
        try {
          user = await authService.getProfile();
        } catch {
          user = { email: email.trim().toLowerCase() };
        }
      }
      user = normalizeAuthUser(user || { email });

      set({ user, isAuthenticated: true, error: null });
      return user;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Login failed. Please check your credentials.');
      set({ error: message, user: null, isAuthenticated: false });
      clearStoredTokens();
      throw new Error(message);
    }
  },

  register: async (formData) => {
    set({ error: null });
    try {
      const response = formData.role === 'faculty'
        ? await authService.registerFaculty(formData)
        : await authService.registerStudent(formData);
      sessionStorage.removeItem('pending_login_verification_challenge');
      sessionStorage.setItem('pending_verification_email', formData.email.trim().toLowerCase());
      set({ error: null });
      return response;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Registration failed.');
      set({ error: message });
      throw new Error(message);
    }
  },

  verifyEmail: async (email, otp, loginChallenge = null) => {
    set({ error: null });
    try {
      const response = await authService.verifyEmail(email, otp, loginChallenge);
      sessionStorage.removeItem('pending_verification_email');
      sessionStorage.removeItem('pending_login_verification_challenge');

      if (response.tokens?.access) {
        localStorage.setItem(config.auth.tokenKey, response.tokens.access);
        if (response.tokens.refresh) {
          localStorage.setItem(config.auth.refreshTokenKey, response.tokens.refresh);
        }
        const user = normalizeAuthUser(response.user || { email });
        set({ user, isAuthenticated: true, error: null });
      } else {
        set({ error: null });
      }
      return response;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Invalid or expired verification code.');
      set({ error: message });
      throw new Error(message);
    }
  },

  resendOTP: async (email, purpose = 'email_verification') => {
    set({ error: null });
    try {
      return await authService.resendOTP(email, purpose);
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Failed to resend the verification code.');
      set({ error: message });
      throw new Error(message);
    }
  },

  forgotPassword: async (email) => {
    set({ error: null });
    try {
      const response = await authService.forgotPassword(email);
      sessionStorage.setItem('password_reset_email', email.trim().toLowerCase());
      return response;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Could not send a password reset code.');
      set({ error: message });
      throw new Error(message);
    }
  },

  resetPassword: async (formData) => {
    set({ error: null });
    try {
      const response = await authService.resetPassword(formData);
      sessionStorage.removeItem('password_reset_email');
      return response;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Could not reset the password.');
      set({ error: message });
      throw new Error(message);
    }
  },

  clearSession: () => {
    clearStoredTokens();
    set({ user: null, isAuthenticated: false, error: null, loading: false });
  },

  logout: () => {
    const refreshToken = localStorage.getItem(config.auth.refreshTokenKey);
    const accessToken = localStorage.getItem(config.auth.tokenKey);
    get().clearSession();

    if (refreshToken && accessToken) {
      authService.logout(refreshToken, accessToken).catch(() => {});
    }
  },

  updateProfile: async (userData) => {
    set({ error: null });
    try {
      const data = await authService.updateProfile(userData, get().user?.id);
      const updatedUser = normalizeAuthUser({ ...get().user, ...(data.profile || data) });
      set({ user: updatedUser, error: null });
      return updatedUser;
    } catch (error) {
      const message = getAuthErrorMessage(error, 'Failed to update profile.');
      set({ error: message });
      throw new Error(message);
    }
  },

  clearError: () => set({ error: null }),
  setUser: (user) => set({ user: user ? normalizeAuthUser(user) : null }),
}));

setAuthenticationExpiredHandler(() => useAuthStore.getState().clearSession());

// Backward-compatible alias
export const authStore = useAuthStore;

export default useAuthStore;
