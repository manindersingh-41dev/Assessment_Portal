import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, BookOpen, Briefcase, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { Card } from '../components/Common.jsx';
import { useAuthStore } from '../store/authStore.js';
import { useNotificationStore } from '../store/notificationStore.js';

const initialForm = {
  first_name: '',
  last_name: '',
  email: '',
  department: '',
  roll_number: '',
  year_of_study: '1',
  employee_id: '',
  designation: '',
  password: '',
  confirm_password: '',
};

const fieldClass = 'w-full rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100';
const labelClass = 'mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300';

export const RegisterPage = () => {
  const [role, setRole] = useState('student');
  const [formData, setFormData] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const navigate = useNavigate();
  const register = useAuthStore((state) => state.register);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const handleChange = (event) => {
    setFormData((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');

    const email = formData.email.trim().toLowerCase();
    if (!email.endsWith('@geetauniversity.edu.in')) {
      setErrorMessage('Use your @geetauniversity.edu.in email address.');
      return;
    }
    if (formData.password.length < 8) {
      setErrorMessage('Your password must be at least 8 characters long.');
      return;
    }
    if (/^\d+$/.test(formData.password)) {
      setErrorMessage('Your password cannot contain only numbers.');
      return;
    }
    if (formData.password !== formData.confirm_password) {
      setErrorMessage('The passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await register({
        ...formData,
        email,
        role,
        password_confirm: formData.confirm_password,
      });
      addNotification('Account created. Enter the code sent to your email.', 'success');
      navigate('/verify-otp', { state: { email, role } });
    } catch (error) {
      setErrorMessage(error.message || 'Registration failed.');
      addNotification(error.message || 'Registration failed.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white/90 p-7 shadow-xl backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
      <div className="mb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Get started</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Create your account</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Register with your university email to use the assessment portal.</p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-800" role="group" aria-label="Account type">
        {[
          { value: 'student', label: 'Student', Icon: BookOpen },
          { value: 'faculty', label: 'Faculty', Icon: Briefcase },
        ].map(({ value, label, Icon }) => (
          <button
            key={value}
            type="button"
            aria-pressed={role === value}
            onClick={() => setRole(value)}
            className={`flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold transition-colors ${role === value ? 'bg-white text-primary-700 shadow-sm dark:bg-slate-900 dark:text-primary-300' : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" /> {label}
          </button>
        ))}
      </div>

      {errorMessage && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-200" role="alert">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
          <p>{errorMessage}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="register-first-name" className={labelClass}>First name</label>
            <div className="relative">
              <UserRound className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input id="register-first-name" className={`${fieldClass} pl-10`} name="first_name" autoComplete="given-name" value={formData.first_name} onChange={handleChange} placeholder="First name" />
            </div>
          </div>
          <div>
            <label htmlFor="register-last-name" className={labelClass}>Last name (optional)</label>
            <input id="register-last-name" className={fieldClass} name="last_name" autoComplete="family-name" value={formData.last_name} onChange={handleChange} placeholder="Last name" />
          </div>
        </div>

        <div>
          <label htmlFor="register-email" className={labelClass}>University email</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input id="register-email" className={`${fieldClass} pl-10`} type="email" name="email" autoComplete="email" autoCapitalize="none" spellCheck="false" required value={formData.email} onChange={handleChange} placeholder="name@geetauniversity.edu.in" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="register-department" className={labelClass}>Department</label>
            <input id="register-department" className={fieldClass} name="department" required value={formData.department} onChange={handleChange} placeholder="e.g. Computer Science" />
          </div>
          {role === 'student' ? (
            <div>
              <label htmlFor="register-roll-number" className={labelClass}>Roll number</label>
              <input id="register-roll-number" className={fieldClass} name="roll_number" required value={formData.roll_number} onChange={handleChange} placeholder="Your roll number" />
            </div>
          ) : (
            <div>
              <label htmlFor="register-employee-id" className={labelClass}>Employee ID</label>
              <input id="register-employee-id" className={fieldClass} name="employee_id" required value={formData.employee_id} onChange={handleChange} placeholder="Your employee ID" />
            </div>
          )}
        </div>

        {role === 'student' ? (
          <div>
            <label htmlFor="register-year" className={labelClass}>Year of study</label>
            <select id="register-year" className={fieldClass} name="year_of_study" value={formData.year_of_study} onChange={handleChange}>
              <option value="1">1st year</option>
              <option value="2">2nd year</option>
              <option value="3">3rd year</option>
              <option value="4">4th year</option>
            </select>
          </div>
        ) : (
          <div>
            <label htmlFor="register-designation" className={labelClass}>Designation</label>
            <input id="register-designation" className={fieldClass} name="designation" required value={formData.designation} onChange={handleChange} placeholder="e.g. Assistant Professor" />
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="register-password" className={labelClass}>Password</label>
            <div className="relative">
              <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input id="register-password" className={`${fieldClass} pl-10`} type="password" name="password" autoComplete="new-password" minLength={8} required value={formData.password} onChange={handleChange} placeholder="At least 8 characters" />
            </div>
          </div>
          <div>
            <label htmlFor="register-confirm-password" className={labelClass}>Confirm password</label>
            <input id="register-confirm-password" className={fieldClass} type="password" name="confirm_password" autoComplete="new-password" minLength={8} required value={formData.confirm_password} onChange={handleChange} placeholder="Re-enter password" />
          </div>
        </div>

        {role === 'faculty' && (
          <p className="rounded-lg bg-amber-50 px-3.5 py-3 text-xs leading-relaxed text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
            Faculty accounts require email verification and administrator approval before sign-in.
          </p>
        )}

        <Button type="submit" variant="primary" fullWidth loading={submitting} className="mt-2 rounded-xl py-2.5 text-sm font-semibold shadow-md shadow-primary-500/20">
          Create {role === 'faculty' ? 'faculty' : 'student'} account <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>

      <p className="mt-6 border-t border-slate-100 pt-5 text-center text-sm text-slate-600 dark:border-slate-800 dark:text-slate-400">
        Already registered? <Link to="/login" className="font-semibold text-primary-600 hover:underline dark:text-primary-400">Sign in</Link>
      </p>
    </Card>
  );
};

export default RegisterPage;
