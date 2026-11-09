import React, { useEffect, useState } from 'react';
import { Activity, ArrowRight, BookOpen, CheckCircle2, Clock3, RefreshCw, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/Button';
import { Alert, Badge, Card } from '../../components/Common';
import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const asList = (data) => Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const metricStyles = [
  'bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300',
  'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
  'bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300',
  'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300',
  'bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300',
  'bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300',
];

const statusStyles = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  compiling: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  compiled: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  executing: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  failed: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200',
};

const FacultyDashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentSubmissions, setRecentSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const addNotification = useNotificationStore((state) => state.addNotification);

  useEffect(() => {
    const controller = new AbortController();
    const loadDashboard = async () => {
      setLoading(true);
      setError('');
      const [statsResult, submissionsResult] = await Promise.allSettled([
        api.get(config.api.endpoints.assessments.statistics, { signal: controller.signal }),
        api.get(config.api.endpoints.results.facultyOverview, {
          params: { page_size: 5 },
          signal: controller.signal,
        }),
      ]);
      if (controller.signal.aborted) return;

      if (statsResult.status === 'fulfilled') setStats(statsResult.value.data || {});
      else {
        const message = statsResult.reason?.response?.data?.detail || 'Could not load faculty statistics.';
        setError(message);
        addNotification(message, 'error');
      }

      if (submissionsResult.status === 'fulfilled') {
        setRecentSubmissions(asList(submissionsResult.value.data));
      } else {
        addNotification('Recent submissions could not be loaded.', 'warning');
      }
      setLoading(false);
    };
    loadDashboard();
    return () => controller.abort();
  }, [addNotification, reloadKey]);

  const metrics = [
    { label: 'Assessments', value: stats?.total_assessments ?? 0, icon: BookOpen },
    { label: 'Active now', value: stats?.active_assessments ?? 0, icon: Activity },
    { label: 'Assigned students', value: stats?.total_students ?? 0, icon: Users },
    { label: 'Submissions', value: stats?.total_submissions ?? 0, icon: CheckCircle2 },
    { label: 'Average score', value: `${Number(stats?.average_score ?? 0).toFixed(1)}%`, icon: BookOpen },
    { label: 'Acceptance rate', value: `${Number(stats?.acceptance_rate ?? 0).toFixed(1)}%`, icon: Clock3 },
  ];

  return (
    <div className="space-y-7 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-primary-700 dark:text-primary-300">Faculty workspace</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">Welcome{user?.first_name ? `, ${user.first_name}` : ''}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Assessment activity and student evaluation at a glance.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setReloadKey((current) => current + 1)} loading={loading}>
            <RefreshCw size={16} />Refresh
          </Button>
          <Button variant="primary" onClick={() => navigate('/faculty/assessments/create')}>Create assessment</Button>
        </div>
      </div>

      {error && <Alert type="error" title="Some dashboard data is unavailable">{error}</Alert>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Faculty statistics">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.label} className="flex items-center gap-4">
              <span className={`rounded-xl p-3 ${metricStyles[index]}`}><Icon size={20} /></span>
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{metric.label}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900 dark:text-white">{loading ? '—' : metric.value}</p>
              </div>
            </Card>
          );
        })}
      </section>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent submissions</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Latest student attempts across your assessments.</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/faculty/results')}>All results<ArrowRight size={15} /></Button>
        </div>

        <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              <tr><th className="px-4 py-3">Student</th><th className="px-4 py-3">Assessment / question</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Verdict</th><th className="px-4 py-3">Marks</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr><td colSpan="5" className="px-4 py-12 text-center text-slate-500">Loading recent submissions…</td></tr>
              ) : recentSubmissions.length ? recentSubmissions.map((submission) => (
                <tr key={submission.submission_id} className="text-slate-700 dark:text-slate-200">
                  <td className="px-4 py-3"><p className="font-medium">{submission.student_name || 'Student'}</p><p className="text-xs text-slate-500">{submission.student_email}</p></td>
                  <td className="px-4 py-3"><p className="font-medium">{submission.assessment_title}</p><p className="text-xs text-slate-500">Q{submission.question_order}: {submission.question_title}</p></td>
                  <td className="px-4 py-3"><Badge className={statusStyles[submission.status] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}>{submission.status_display || submission.status}</Badge></td>
                  <td className="px-4 py-3 capitalize">{(submission.verdict_display || submission.verdict || '').replaceAll('_', ' ')}</td>
                  <td className="px-4 py-3">{submission.marks_obtained ?? '—'}</td>
                </tr>
              )) : (
                <tr><td colSpan="5" className="px-4 py-12 text-center text-slate-500">No submissions yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default FacultyDashboard;
