import React from 'react';
import { ArrowLeft, Heart, Sparkles, Sun } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/Button';

const ChildrenDayPage = () => {
  const navigate = useNavigate();

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-amber-100 via-rose-50 to-sky-100 px-5 py-12 text-slate-900 dark:from-slate-950 dark:via-indigo-950 dark:to-slate-900 dark:text-white">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-20 top-10 h-64 w-64 rounded-full bg-amber-300/40 blur-3xl dark:bg-amber-400/10" />
        <div className="absolute -right-16 bottom-0 h-72 w-72 rounded-full bg-fuchsia-300/40 blur-3xl dark:bg-fuchsia-400/10" />
        <Sparkles className="absolute left-[14%] top-[18%] h-8 w-8 text-amber-500/70" />
        <Sparkles className="absolute right-[16%] top-[25%] h-6 w-6 text-fuchsia-500/70" />
        <Heart className="absolute bottom-[18%] left-[20%] h-7 w-7 -rotate-12 text-rose-400/70" />
        <Sun className="absolute bottom-[16%] right-[18%] h-9 w-9 text-orange-400/70" />
      </div>

      <section className="relative w-full max-w-2xl rounded-[2rem] border border-white/70 bg-white/80 p-7 text-center shadow-2xl shadow-rose-900/10 backdrop-blur-xl sm:p-12 dark:border-white/10 dark:bg-slate-900/80 dark:shadow-black/20">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-amber-300 to-rose-400 text-4xl shadow-lg shadow-rose-500/20" role="img" aria-label="Celebration">
          🎈
        </div>
        <p className="mt-7 text-sm font-bold uppercase tracking-[0.22em] text-rose-600 dark:text-rose-300">November 14 · Children’s Day</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">Keep being curious!</h1>
        <p className="mx-auto mt-5 max-w-lg text-base leading-7 text-slate-600 sm:text-lg dark:text-slate-300">
          Today is for big ideas, bright questions, and a little extra fun. Take a break from assessments and celebrate the joy of learning.
        </p>

        <div className="mx-auto mt-8 max-w-lg rounded-2xl border border-amber-200 bg-amber-50/90 p-4 text-left text-sm leading-6 text-amber-950 dark:border-amber-900/70 dark:bg-amber-950/40 dark:text-amber-100">
          Assessment sessions are unavailable today, including attempts already in progress. If you started a timed assessment, its timer may continue to count down while access is blocked.
        </div>

        <Button className="mx-auto mt-8" size="lg" onClick={() => navigate('/student/assessments')}>
          <ArrowLeft size={17} />Back to my assessments
        </Button>
        <p className="mt-5 text-xs font-medium text-slate-500 dark:text-slate-400">Wishing you a joyful Children’s Day ✨</p>
      </section>
    </main>
  );
};

export default ChildrenDayPage;
