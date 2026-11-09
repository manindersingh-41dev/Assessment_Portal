import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, ArrowRight, Mail } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { Card } from '../components/Common.jsx';
import { useAuthStore } from '../store/authStore.js';
import { useNotificationStore } from '../store/notificationStore.js';

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const forgotPassword = useAuthStore((state) => state.forgotPassword);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSubmitting(true);
    const normalizedEmail = email.trim().toLowerCase();

    try {
      await forgotPassword(normalizedEmail);
      addNotification('A password reset code has been sent to your email.', 'success');
      navigate('/reset-password', { state: { email: normalizedEmail } });
    } catch (error) {
      setErrorMessage(error.message || 'Could not send a password reset code.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white/90 p-7 shadow-xl backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
      <Link to="/login" className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to sign in
      </Link>
      <div className="mb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Account recovery</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Forgot your password?</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
          Enter the email on your account and we’ll send a one-time reset code.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-200" role="alert">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <p>{errorMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="forgot-email" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">University email</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="forgot-email"
              name="email"
              type="email"
              autoComplete="email"
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
        <Button type="submit" variant="primary" fullWidth loading={submitting} className="rounded-xl py-2.5 text-sm font-semibold shadow-md shadow-primary-500/20">
          Send reset code <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>
    </Card>
  );
};

export default ForgotPasswordPage;
