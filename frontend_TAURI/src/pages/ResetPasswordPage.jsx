import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Check, Eye, EyeOff, KeyRound, LockKeyhole, Mail } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { Card } from '../components/Common.jsx';
import { useAuthStore } from '../store/authStore.js';
import { useNotificationStore } from '../store/notificationStore.js';

const fieldClass = 'w-full rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100';

const ResetPasswordPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState(() => location.state?.email || sessionStorage.getItem('password_reset_email') || '');
  const [otp, setOtp] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const resetPassword = useAuthStore((state) => state.resetPassword);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^\d{6}$/.test(otp)) {
      setErrorMessage('Enter the 6-digit code from your email.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Your password must be at least 8 characters long.');
      return;
    }
    if (/^\d+$/.test(password)) {
      setErrorMessage('Your password cannot contain only numbers.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('The passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword({
        email: normalizedEmail,
        otp,
        new_password: password,
        new_password_confirm: confirmPassword,
      });
      addNotification('Your password has been reset. Sign in with the new password.', 'success');
      navigate('/login', { replace: true });
    } catch (error) {
      setErrorMessage(error.message || 'Could not reset your password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white/90 p-7 shadow-xl backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
      <Link to="/forgot-password" className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Request a new code
      </Link>
      <div className="mb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Secure your account</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Set a new password</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">Enter the code we emailed you and choose a new password.</p>
      </div>

      {errorMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-200" role="alert">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <p>{errorMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="reset-email" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">University email</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="reset-email" className={`${fieldClass} pl-10`} type="email" autoComplete="email" autoCapitalize="none" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@geetauniversity.edu.in" />
          </div>
        </div>
        <div>
          <label htmlFor="reset-otp" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Reset code</label>
          <div className="relative">
            <KeyRound className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="reset-otp" className={`${fieldClass} pl-10 font-mono tracking-[0.3em]`} type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" />
          </div>
        </div>
        <div>
          <label htmlFor="reset-password" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">New password</label>
          <div className="relative">
            <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="reset-password" className={`${fieldClass} pl-10 pr-12`} type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" />
            <button type="button" onClick={() => setShowPassword((visible) => !visible)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:text-slate-200" aria-label={showPassword ? 'Hide password' : 'Show password'}>
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">Use at least 8 characters and include something other than numbers.</p>
        </div>
        <div>
          <label htmlFor="reset-confirm-password" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Confirm new password</label>
          <div className="relative">
            <input id="reset-confirm-password" className={`${fieldClass} pr-10`} type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter your password" />
            {confirmPassword && password === confirmPassword && <Check className="absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-500" aria-label="Passwords match" />}
          </div>
        </div>

        <Button type="submit" variant="primary" fullWidth loading={submitting} disabled={!email.trim() || otp.length !== 6} className="rounded-xl py-2.5 text-sm font-semibold shadow-md shadow-primary-500/20">
          Reset password
        </Button>
      </form>
    </Card>
  );
};

export default ResetPasswordPage;
