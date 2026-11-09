/**
 * Central HTTP API Client
 * - Configures Axios with base URL and timeout
 * - Request interceptor: injects Bearer JWT access token
 * - Response interceptor: handles 401 Unauthorized with token refresh & queueing
 */

import axios from 'axios';
import { config } from '../constants/config.js';

const apiClient = axios.create({
  baseURL: config.api.baseURL,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Flag to coordinate multiple concurrent 401s
let isRefreshing = false;
let failedQueue = [];
let authenticationExpiredHandler = null;

export const setAuthenticationExpiredHandler = (handler) => {
  authenticationExpiredHandler = typeof handler === 'function' ? handler : null;
};

const handleAuthenticationExpired = () => {
  authenticationExpiredHandler?.();
};

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor: attach Authorization header
apiClient.interceptors.request.use(
  (reqConfig) => {
    const token = localStorage.getItem(config.auth.tokenKey);
    if (token) {
      reqConfig.headers.Authorization = `Bearer ${token}`;
    }
    return reqConfig;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: refresh token on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh on 401 if not already retried and not a login/token call
    const isAuthRoute = originalRequest?.url?.includes('/token/') || originalRequest?.url?.includes('/login');

    if (error.response?.status === 401 && !originalRequest?._retry && !isAuthRoute) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem(config.auth.refreshTokenKey);
      if (!refreshToken) {
        isRefreshing = false;
        localStorage.removeItem(config.auth.tokenKey);
        localStorage.removeItem(config.auth.refreshTokenKey);
        processQueue(error, null);
        handleAuthenticationExpired();
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${config.api.baseURL}${config.api.endpoints.auth.refresh}`, {
          refresh: refreshToken,
        });

        const newAccessToken = response.data.access;
        localStorage.setItem(config.auth.tokenKey, newAccessToken);
        apiClient.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

        processQueue(null, newAccessToken);
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem(config.auth.tokenKey);
        localStorage.removeItem(config.auth.refreshTokenKey);
        handleAuthenticationExpired();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
