import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, BarChart3, ChevronDown, ChevronUp, RefreshCw, Search } from 'lucide-react';
import { Button } from '../../components/Button';
import { Alert, Badge, Card } from '../../components/Common';
import { Input } from '../../components/Input';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const statusStyles = {
  evaluated: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  processing: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  incomplete: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  evaluation_failed: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200',
};
const PAGE_SIZE = 20;

const dateLabel = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const StudentResultsPage = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [expandedResult, setExpandedResult] = useState(null);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const addNotification = useNotificationStore((state) => state.addNotification);

  useEffect(() => {
    const controller = new AbortController();
    const loadResults = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get(config.api.endpoints.results.studentResults, {
          params: { page, page_size: PAGE_SIZE },
          signal: controller.signal,
        });
        const data = response.data;
        setResults(Array.isArray(data) ? data : data?.results || []);
        setPageCount(Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE)));
      } catch (requestError) {
        if (controller.signal.aborted) return;
        const message = requestError.response?.data?.detail || 'Could not load your results.';
        setError(message);
        addNotification(message, 'error');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    loadResults();
    return () => controller.abort();
  }, [addNotification, page, reloadKey]);

  const filteredResults = useMemo(() => {
    const query = search.trim().toLowerCase();
    return results.filter((result) => !query || String(result.assessment_title || '').toLowerCase().includes(query));
  }, [results, search]);

  const evaluatedResults = results.filter((result) => result.status === 'evaluated');
  const averageScore = evaluatedResults.length
    ? evaluatedResults.reduce((sum, result) => sum + (Number(result.percentage) || 0), 0) / evaluatedResults.length
    : 0;
  const passedTests = results.reduce((sum, result) => sum + (Number(result.passed_test_cases) || 0), 0);
  const totalTests = results.reduce((sum, result) => sum + (Number(result.total_test_cases) || 0), 0);

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My results</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Scorecards and question-level evaluation for submitted assessments.</p>
        </div>
        <Button variant="secondary" onClick={() => setReloadKey((current) => current + 1)} loading={loading}>
          <RefreshCw size={16} />Refresh
        </Button>
      </div>

      {error && <Alert type="error" title="Results could not be loaded">{error}</Alert>}

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard label="Scorecards" value={results.length} detail="Submitted assessments" />
        <MetricCard label="Average score" value={evaluatedResults.length ? `${averageScore.toFixed(1)}%` : '—'} detail="Evaluated scorecards" />
        <MetricCard label="Test cases passed" value={`${passedTests} / ${totalTests}`} detail="Best completed or latest attempt per question" />
      </div>

      <Card className="space-y-4">
        <div className="relative max-w-md">
          <Input
            label="Search this page"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by assessment name"
            aria-label="Search results"
            className="pl-10"
          />
          <Search size={16} className="pointer-events-none absolute left-3 top-[38px] text-slate-400" aria-hidden="true" />
        </div>

        <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Assessment</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Percentage</th>
                <th className="px-4 py-3">Tests passed</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3"><span className="sr-only">Breakdown</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr><td colSpan="7" className="px-4 py-14 text-center text-slate-500">Loading results…</td></tr>
              ) : filteredResults.length ? filteredResults.map((result) => (
                <React.Fragment key={result.assignment_id || result.id}>
                  <tr className="text-slate-700 dark:text-slate-200">
                    <td className="px-4 py-4 font-medium">{result.assessment_title}</td>
                    <td className="px-4 py-4">{result.marks_obtained} / {result.total_marks}</td>
                    <td className="px-4 py-4 font-semibold">{Number(result.percentage || 0).toFixed(1)}%</td>
                    <td className="px-4 py-4">{result.passed_test_cases ?? 0} / {result.total_test_cases ?? 0}</td>
                    <td className="px-4 py-4">
                      <Badge className={statusStyles[result.status] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}>
                        {(result.status || 'processing').replaceAll('_', ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-4 text-slate-500 dark:text-slate-400">{dateLabel(result.submitted_at)}</td>
                    <td className="px-4 py-4 text-right">
                      <Button size="sm" variant="ghost" aria-expanded={expandedResult === result.assignment_id}
                        onClick={() => setExpandedResult((current) => current === result.assignment_id ? null : result.assignment_id)}>
                        {expandedResult === result.assignment_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        Breakdown
                      </Button>
                    </td>
                  </tr>
                  {expandedResult === result.assignment_id && (
                    <tr>
                      <td colSpan="7" className="bg-slate-50 px-4 py-4 dark:bg-slate-900/70">
                        <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
                          <table className="w-full min-w-[550px] text-left text-xs">
                            <thead className="text-slate-500 dark:text-slate-400">
                              <tr><th className="py-2 pr-4">Question</th><th className="py-2 pr-4">Score</th><th className="py-2 pr-4">Tests</th><th className="py-2">Verdict</th></tr>
                            </thead>
                            <tbody>
                              {(result.question_results || []).map((question) => (
                                <tr key={question.question_id} className="border-t border-slate-200 dark:border-slate-800">
                                  <td className="py-2 pr-4">Q{question.question_order}: {question.question_title}</td>
                                  <td className="py-2 pr-4">{question.marks_obtained} / {question.total_marks}</td>
                                  <td className="py-2 pr-4">{question.passed_test_cases} / {question.total_test_cases}</td>
                                  <td className="py-2 capitalize">{(question.verdict || '').replaceAll('_', ' ')}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )) : (
                <tr><td colSpan="7" className="px-4 py-14 text-center text-slate-500">
                  {search ? 'No results match that assessment name.' : 'Your scorecards will appear after you submit an assessment.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex items-center justify-between text-sm">
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
    </div>
  );
};

const MetricCard = ({ label, value, detail }) => (
  <Card className="flex items-start gap-4">
    <span className="rounded-xl bg-primary-50 p-3 text-primary-700 dark:bg-primary-950 dark:text-primary-300"><BarChart3 size={20} /></span>
    <div><p className="text-sm text-slate-500 dark:text-slate-400">{label}</p><p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div>
  </Card>
);

export default StudentResultsPage;
