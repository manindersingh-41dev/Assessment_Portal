import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, KeyRound, RefreshCw } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { Card } from '../components/Common.jsx';
import { useAuthStore } from '../store/authStore.js';
import { useNotificationStore } from '../store/notificationStore.js';

const fieldClass = 'w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100';
const roleHome = (role) => role === 'faculty' ? '/faculty/dashboard' : '/student/dashboard';

export const VerifyOTPPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState(() => location.state?.email || sessionStorage.getItem('pending_verification_email') || '');
  const [otp, setOtp] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [countdown, setCountdown] = useState(60);
  const verifyEmail = useAuthStore((state) => state.verifyEmail);
  const resendOTP = useAuthStore((state) => state.resendOTP);
  const addNotification = useNotificationStore((state) => state.addNotification);

  useEffect(() => {
    if (countdown <= 0) return undefined;
    const timeout = window.setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => window.clearTimeout(timeout);
  }, [countdown]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail) {
      setErrorMessage('Enter the email address you registered with.');
      return;
    }
    if (!/^\d{6}$/.test(otp)) {
      setErrorMessage('Enter the 6-digit verification code.');
      return;
    }

    setSubmitting(true);
    try {
      const loginChallenge = sessionStorage.getItem('pending_login_verification_challenge');
      const result = await verifyEmail(normalizedEmail, otp, loginChallenge);

      if (result.auto_login) {
        addNotification('Email verified. You are now signed in.', 'success');
        navigate(roleHome(result.user?.role), { replace: true });
        return;
      }

      addNotification(result.next_step || 'Email verified. You can now sign in.', 'success');
      navigate('/login', { replace: true, state: { email: normalizedEmail } });
    } catch (error) {
      setErrorMessage(error.message || 'Email verification failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (countdown > 0 || !normalizedEmail) return;

    setResending(true);
    setErrorMessage('');
    try {
      await resendOTP(normalizedEmail, 'email_verification');
      addNotification('A new verification code has been sent.', 'info');
      setCountdown(60);
    } catch (error) {
      setErrorMessage(error.message || 'Could not resend the verification code.');
    } finally {
      setResending(false);
    }
  };

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white/90 p-7 shadow-xl backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
      <div className="mb-6 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300">
          <KeyRound className="h-6 w-6" aria-hidden="true" />
        </div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">One more step</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Verify your email</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {location.state?.verificationSent
            ? 'A new 6-digit verification code was sent to your email. Enter it below.'
            : 'Enter the 6-digit code we sent you.'}
        </p>
      </div>

      {errorMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-200" role="alert">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <p>{errorMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="verification-email" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">University email</label>
          <input
            id="verification-email"
            className={fieldClass}
            type="email"
            autoComplete="email"
            autoCapitalize="none"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@geetauniversity.edu.in"
          />
        </div>
        <div>
          <label htmlFor="verification-code" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Verification code</label>
          <input
            id="verification-code"
            className={`${fieldClass} py-3 text-center font-mono text-2xl font-bold tracking-[0.45em]`}
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={otp}
            onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
          />
        </div>

        <Button type="submit" variant="primary" fullWidth loading={submitting} disabled={!email.trim() || otp.length !== 6} className="rounded-xl py-2.5 text-sm font-semibold shadow-md shadow-primary-500/20">
          Verify email <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5 text-sm dark:border-slate-800">
        <span className="text-slate-500 dark:text-slate-400">Didn't receive the email?</span>
        <button type="button" onClick={handleResend} disabled={!email.trim() || countdown > 0 || resending} className="inline-flex items-center gap-2 font-semibold text-primary-600 hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline dark:text-primary-400">
          <RefreshCw className={`h-3.5 w-3.5 ${resending ? 'animate-spin' : ''}`} aria-hidden="true" />
          {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
        </button>
      </div>

      <p className="mt-5 text-center text-sm text-slate-500 dark:text-slate-400">
        Wrong email? <Link to="/register" className="font-semibold text-primary-600 hover:underline dark:text-primary-400">Register again</Link>
      </p>
    </Card>
  );
};

export default VerifyOTPPage;
