import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { Card } from '../components/Common.jsx';
import { useAuthStore } from '../store/authStore.js';
import { useNotificationStore } from '../store/notificationStore.js';

const roleHome = (role) => role === 'faculty' ? '/faculty/dashboard' : '/student/dashboard';

export const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState(() => location.state?.email || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const login = useAuthStore((state) => state.login);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSubmitting(true);

    try {
      const user = await login(email, password);
      if (user?.verificationRequired) {
        addNotification('Your email is not verified. A new verification code was sent.', 'info');
        navigate('/verify-otp', {
          replace: true,
          state: {
            email: user.email,
            role: user.role,
            verificationSent: true,
          },
        });
        return;
      }

      addNotification('Signed in successfully.', 'success');

      const requestedPath = location.state?.from?.pathname;
      const requestedRole = requestedPath?.startsWith('/faculty/')
        ? 'faculty'
        : requestedPath?.startsWith('/student/') || requestedPath?.startsWith('/assessment/')
          ? 'student'
          : null;
      const canReturnToPath = requestedPath && requestedRole === user.role;
      const destination = canReturnToPath ? requestedPath : roleHome(user.role);
      navigate(destination, { replace: true });
    } catch (error) {
      setErrorMessage(error.message || 'Login failed. Please check your credentials.');
      addNotification(error.message || 'Login failed.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white/90 p-7 shadow-xl backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
      <div className="mb-7">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">
          Welcome back
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Sign in to your account</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Use your Geeta University email to continue.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-200" role="alert">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" />
          <p>{errorMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="login-email" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
            University email
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck="false"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@geetauniversity.edu.in"
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 py-2.5 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100"
            />
          </div>
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between gap-4">
            <label htmlFor="login-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
            <Link to="/forgot-password" className="text-xs font-semibold text-primary-600 hover:underline dark:text-primary-400">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="login-password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 py-2.5 pl-10 pr-12 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100"
            />
            <button
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:text-slate-200"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <Button type="submit" variant="primary" fullWidth loading={submitting} className="mt-2 rounded-xl py-2.5 text-sm font-semibold shadow-md shadow-primary-500/20">
          Sign in <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>

      <p className="mt-6 border-t border-slate-100 pt-5 text-center text-sm text-slate-600 dark:border-slate-800 dark:text-slate-400">
        New to the portal?{' '}
        <Link to="/register" className="font-semibold text-primary-600 hover:underline dark:text-primary-400">
          Create an account
        </Link>
      </p>
    </Card>
  );
};

export default LoginPage;
