/** Authentication and role-aware route gate. */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore.js';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const getHomePath = (role) => {
  if (role === 'faculty') return '/faculty/dashboard';
  if (role === 'student') return '/student/dashboard';
  return '/login';
};

export const ProtectedRoute = ({ children, requiredRole = null, guestOnly = false }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const loading = useAuthStore((state) => state.loading);
  const user = useAuthStore((state) => state.user);
  const location = useLocation();
  const content = children || <Outlet />;

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-50 dark:bg-slate-950" aria-label="Loading session">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (guestOnly) {
    if (!isAuthenticated) return content;

    const requestedPath = location.state?.from?.pathname;
    const requestedRole = requestedPath?.startsWith('/faculty/')
      ? 'faculty'
      : requestedPath?.startsWith('/student/') || requestedPath?.startsWith('/assessment/')
        ? 'student'
        : null;
    const canReturnToPath = requestedPath && requestedPath !== '/dashboard' && (!requestedRole || requestedRole === user?.role);
    return <Navigate to={canReturnToPath ? requestedPath : getHomePath(user?.role)} replace />;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to={getHomePath(user.role)} replace />;
  }

  return content;
};

export default ProtectedRoute;
