import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, RefreshCw, Search } from 'lucide-react';
import { Button } from '../../components/Button';
import { Alert, Badge, Card } from '../../components/Common';
import { Input } from '../../components/Input';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const PAGE_SIZE = 20;
const statusStyles = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  compiling: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  compiled: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  executing: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  failed: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200',
};

const dateLabel = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const StudentSubmissionsPage = () => {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const addNotification = useNotificationStore((state) => state.addNotification);

  useEffect(() => {
    const controller = new AbortController();
    const loadSubmissions = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get(config.api.endpoints.results.studentHistory, {
          params: { page, page_size: PAGE_SIZE },
          signal: controller.signal,
        });
        const data = response.data;
        setSubmissions(Array.isArray(data) ? data : data?.results || []);
        setPageCount(Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE)));
      } catch (requestError) {
        if (controller.signal.aborted) return;
        const message = requestError.response?.data?.detail || 'Could not load your submission history.';
        setError(message);
        addNotification(message, 'error');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    loadSubmissions();
    return () => controller.abort();
  }, [addNotification, page, reloadKey]);

  const filteredSubmissions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return submissions;
    return submissions.filter((submission) => [
      submission.assessment_title,
      submission.question_title,
      submission.status_display,
      submission.verdict_display,
    ].some((value) => String(value || '').toLowerCase().includes(query)));
  }, [search, submissions]);

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Submission history</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Review your code attempts and evaluation status.</p>
        </div>
        <Button variant="secondary" onClick={() => setReloadKey((current) => current + 1)} loading={loading}>
          <RefreshCw size={16} />Refresh
        </Button>
      </div>

      {error && <Alert type="error" title="Submissions could not be loaded">{error}</Alert>}

      <Card className="space-y-4">
        <div className="relative max-w-md">
          <Input
            label="Search submissions"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Assessment, question, or status"
            aria-label="Search submissions"
            className="pl-10"
          />
          <Search size={16} className="pointer-events-none absolute left-3 top-[38px] text-slate-400" aria-hidden="true" />
        </div>

        <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Assessment</th>
                <th className="px-4 py-3">Question</th>
                <th className="px-4 py-3">Attempt</th>
                <th className="px-4 py-3">Evaluation</th>
                <th className="px-4 py-3">Tests passed</th>
                <th className="px-4 py-3">Marks</th>
                <th className="px-4 py-3">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr><td colSpan="7" className="px-4 py-14 text-center text-slate-500">Loading submission history…</td></tr>
              ) : filteredSubmissions.length ? filteredSubmissions.map((submission) => (
                <tr key={submission.submission_id} className="text-slate-700 dark:text-slate-200">
                  <td className="px-4 py-4 font-medium">{submission.assessment_title || 'Assessment'}</td>
                  <td className="px-4 py-4">Q{submission.question_order}: {submission.question_title}</td>
                  <td className="px-4 py-4">#{submission.attempt_number}</td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={statusStyles[submission.status] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}>
                        {submission.status_display || submission.status}
                      </Badge>
                      <span className="text-xs capitalize text-slate-500 dark:text-slate-400">
                        {(submission.verdict_display || submission.verdict || '').replaceAll('_', ' ')}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    {submission.passed_test_cases ?? 0} / {submission.total_test_cases ?? 0}
                  </td>
                  <td className="px-4 py-4">{submission.marks_obtained ?? '—'}</td>
                  <td className="px-4 py-4 text-slate-500 dark:text-slate-400">{dateLabel(submission.created_at)}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" className="px-4 py-14 text-center text-slate-500">
                    {search ? 'No submissions match that search.' : 'No submissions yet. Your attempts will appear here.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 pt-4 text-sm dark:border-slate-800">
          <span className="text-slate-500">Page {page} of {pageCount}</span>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>
              <ArrowLeft size={15} />Previous
            </Button>
            <Button size="sm" variant="secondary" disabled={page >= pageCount || loading} onClick={() => setPage((current) => current + 1)}>
              Next<ArrowRight size={15} />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default StudentSubmissionsPage;
