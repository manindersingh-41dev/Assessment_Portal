import React, { useEffect, useState } from 'react';
import { CheckCircle2, CircleUserRound, Mail, Save } from 'lucide-react';
import { Alert, Card } from '../../components/Common';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';

const FacultyProfilePage = () => {
  const user = useAuthStore((state) => state.user);
  const updateProfile = useAuthStore((state) => state.updateProfile);
  const addNotification = useNotificationStore((state) => state.addNotification);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ first_name: '', last_name: '' });

  useEffect(() => {
    setFormData({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
    });
  }, [user?.first_name, user?.last_name]);

  const handleChange = (event) => {
    setFormData((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await updateProfile(formData);
      addNotification('Profile updated successfully.', 'success');
    } catch (updateError) {
      const message = updateError.message || 'Could not update your profile.';
      setError(message);
      addNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Your profile';

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
      <div>
        <p className="text-sm font-medium text-primary-700 dark:text-primary-300">Account settings</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">My profile</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Manage the name shown across the assessment portal.</p>
      </div>

      {error && <Alert type="error" title="Profile update failed">{error}</Alert>}

      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <Card className="h-fit">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-primary-800 dark:bg-primary-950 dark:text-primary-200">
              <CircleUserRound size={30} />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-lg font-semibold text-slate-900 dark:text-white">{fullName}</h2>
              <p className="capitalize text-sm text-slate-500 dark:text-slate-400">{user?.role || 'User'}</p>
            </div>
          </div>
          <div className="mt-6 space-y-4 border-t border-slate-100 pt-5 dark:border-slate-800">
            <div className="flex items-start gap-3">
              <Mail size={17} className="mt-0.5 text-slate-400" />
              <div className="min-w-0"><p className="text-xs text-slate-500">Email address</p><p className="break-all text-sm font-medium text-slate-800 dark:text-slate-200">{user?.email || '—'}</p></div>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 size={17} className={user?.is_email_verified ? 'text-emerald-600' : 'text-amber-500'} />
              <span className="text-sm text-slate-600 dark:text-slate-300">{user?.is_email_verified ? 'Email verified' : 'Email not verified'}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Personal information</h2>
          <p className="mb-5 mt-1 text-sm text-slate-500 dark:text-slate-400">Your email address is managed by your account and cannot be changed here.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="First name" name="first_name" value={formData.first_name} onChange={handleChange} required disabled={loading} autoComplete="given-name" />
            <Input label="Last name" name="last_name" value={formData.last_name} onChange={handleChange} disabled={loading} autoComplete="family-name" />
            <Input label="Email" value={user?.email || ''} disabled readOnly />
            <div className="flex justify-end border-t border-slate-100 pt-4 dark:border-slate-800">
              <Button type="submit" loading={loading}><Save size={16} />Save changes</Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default FacultyProfilePage;
