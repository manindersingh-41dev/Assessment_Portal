import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';
import { Button } from '../components/Button.jsx';
import { useAuthStore } from '../store/authStore.js';

export const NotFoundPage = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);
  const homePath = !isAuthenticated
    ? '/login'
    : user?.role === 'faculty'
      ? '/faculty/dashboard'
      : '/student/dashboard';

  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-4 py-12 dark:bg-slate-950">
      <div className="w-full max-w-lg text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 ring-1 ring-primary-600/10 dark:bg-primary-950/60 dark:text-primary-300 dark:ring-primary-400/20">
          <Compass className="h-8 w-8" aria-hidden="true" />
        </div>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-primary-600 dark:text-primary-400">Page not found</p>
        <h1 className="mt-3 text-5xl font-bold tracking-tight text-slate-900 dark:text-white">404</h1>
        <p className="mx-auto mt-4 max-w-sm text-base leading-relaxed text-slate-600 dark:text-slate-400">
          This address doesn’t lead to a page in the assessment portal. Check the link or return to your workspace.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button variant="primary" onClick={() => navigate(homePath, { replace: true })}>
            Go to {isAuthenticated ? 'dashboard' : 'sign in'}
          </Button>
          <Button variant="outline" icon={ArrowLeft} onClick={() => navigate(-1)}>
            Go back
          </Button>
        </div>
      </div>
    </main>
  );
};

export default NotFoundPage;
