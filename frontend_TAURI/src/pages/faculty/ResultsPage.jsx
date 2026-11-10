import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDownToLine, ChevronDown, Eye, RefreshCw, Search } from 'lucide-react';
import { Button } from '../../components/Button';
import { Alert, Badge, Card } from '../../components/Common';
import { Input } from '../../components/Input';
import { Modal } from '../../components/Modal';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const PAGE_SIZE = 100;
const asList = (data) => Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];
const statusStyles = {
  pending: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  compiling: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  compiled: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  executing: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  failed: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200',
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  evaluated: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  processing: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  incomplete: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  in_progress: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  not_submitted: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  evaluation_failed: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200',
  active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
  draft: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  scheduled: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200',
  closed: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  archived: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
};

const errorMessage = (error, fallback) => error?.response?.data?.detail
  || error?.response?.data?.error
  || fallback;

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const statusLabel = (row) => {
  const hasSubmission = (row.question_results || []).some((question) => question.submission_id);
  if (row.status === 'in_progress' && !hasSubmission) return 'Not submitted';
  return (row.status || 'processing').replaceAll('_', ' ');
};

const ACTIVE_EVALUATION_STATUSES = new Set(['pending', 'compiling', 'compiled', 'executing']);

const FacultyResultsPage = () => {
  const [assessments, setAssessments] = useState([]);
  const [assessmentLoading, setAssessmentLoading] = useState(true);
  const [assessmentError, setAssessmentError] = useState('');
  const [expandedAssessmentId, setExpandedAssessmentId] = useState(null);
  const [assessmentResults, setAssessmentResults] = useState({});
  const [exportingAssessmentId, setExportingAssessmentId] = useState(null);
  const [search, setSearch] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [expandedResult, setExpandedResult] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [retryingSubmissionId, setRetryingSubmissionId] = useState(null);
  const addNotification = useNotificationStore((state) => state.addNotification);
  const resultControllersRef = useRef(new Map());
  const detailControllerRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    const loadAssessments = async () => {
      setAssessmentLoading(true);
      setAssessmentError('');
      setAssessmentResults({});
      setExpandedAssessmentId(null);
      const loadedAssessments = [];
      const visitedPages = new Set();
      let url = config.api.endpoints.assessments.list;
      let isFirstPage = true;

      try {
        while (url && !visitedPages.has(url)) {
          visitedPages.add(url);
          const response = await api.get(url, {
            ...(isFirstPage ? { params: { page_size: PAGE_SIZE } } : {}),
            signal: controller.signal,
          });
          const data = response.data;
          loadedAssessments.push(...asList(data));
          url = Array.isArray(data) ? null : data?.next || null;
          isFirstPage = false;
        }
        if (!controller.signal.aborted) setAssessments(loadedAssessments);
      } catch (requestError) {
        if (controller.signal.aborted) return;
        const message = errorMessage(requestError, 'Could not load your assessments.');
        setAssessmentError(message);
        addNotification(message, 'error');
      } finally {
        if (!controller.signal.aborted) setAssessmentLoading(false);
      }
    };

    loadAssessments();
    return () => controller.abort();
  }, [addNotification, reloadKey]);

  const loadAssessmentResults = useCallback(async (assessmentId, page = 1) => {
    resultControllersRef.current.get(assessmentId)?.abort();
    const controller = new AbortController();
    resultControllersRef.current.set(assessmentId, controller);
    setAssessmentResults((current) => ({
      ...current,
      [assessmentId]: {
        ...current[assessmentId],
        page,
        loading: true,
        error: '',
      },
    }));

    try {
      const response = await api.get(config.api.endpoints.results.facultyStudentWiseResults, {
        params: { assessment_id: assessmentId, page, page_size: PAGE_SIZE },
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      const data = response.data;
      setAssessmentResults((current) => ({
        ...current,
        [assessmentId]: {
          results: asList(data),
          count: data?.count ?? data?.length ?? 0,
          page,
          hasNext: Boolean(data?.next),
          hasPrevious: Boolean(data?.previous),
          loading: false,
          loaded: true,
          error: '',
        },
      }));
    } catch (requestError) {
      if (controller.signal.aborted) return;
      const message = errorMessage(requestError, 'Could not load results for this assessment.');
      setAssessmentResults((current) => ({
        ...current,
        [assessmentId]: {
          ...current[assessmentId],
          loading: false,
          error: message,
        },
      }));
    } finally {
      if (resultControllersRef.current.get(assessmentId) === controller) {
        resultControllersRef.current.delete(assessmentId);
      }
    }
  }, []);

  useEffect(() => {
    if (!expandedAssessmentId) return undefined;
    const resultSet = assessmentResults[expandedAssessmentId];
    if (!resultSet?.loaded || resultSet.loading) return undefined;
    const hasActiveEvaluations = (resultSet.results || []).some((row) => (
      row.question_results || []
    ).some((question) => ACTIVE_EVALUATION_STATUSES.has(question.status)));
    if (!hasActiveEvaluations) return undefined;

    const interval = window.setInterval(() => {
      loadAssessmentResults(expandedAssessmentId, resultSet.page || 1);
    }, 8000);
    return () => window.clearInterval(interval);
  }, [assessmentResults, expandedAssessmentId, loadAssessmentResults]);

  useEffect(() => () => {
    resultControllersRef.current.forEach((controller) => controller.abort());
    detailControllerRef.current?.abort();
  }, []);

  const filteredAssessments = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return assessments;
    return assessments.filter((assessment) => [assessment.title, assessment.description, assessment.status]
      .some((value) => String(value || '').toLowerCase().includes(query)));
  }, [assessments, search]);

  const toggleAssessment = (assessmentId) => {
    if (expandedAssessmentId === assessmentId) {
      setExpandedAssessmentId(null);
      return;
    }
    setExpandedAssessmentId(assessmentId);
    const current = assessmentResults[assessmentId];
    if (!current?.loaded && !current?.loading) loadAssessmentResults(assessmentId, 1);
  };

  const handleRefresh = () => {
    resultControllersRef.current.forEach((controller) => controller.abort());
    resultControllersRef.current.clear();
    setAssessmentResults({});
    setReloadKey((current) => current + 1);
  };

  const handleExport = async (assessmentId) => {
    setExportingAssessmentId(assessmentId);
    try {
      const response = await api.get(config.api.endpoints.results.exportCSV, {
        params: { assessment_id: assessmentId },
        responseType: 'blob',
      });
      const downloadUrl = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `assessment-${assessmentId}-results.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
      addNotification('Results CSV downloaded.', 'success');
    } catch (exportError) {
      addNotification(errorMessage(exportError, 'Could not export this assessment.'), 'error');
    } finally {
      setExportingAssessmentId(null);
    }
  };

  const handleRetryEvaluation = async (assessmentId, submissionId, page) => {
    setRetryingSubmissionId(submissionId);
    try {
      await api.post(config.api.endpoints.submissions.retryEvaluation(submissionId));
      addNotification('Evaluation retry queued.', 'success');
      await loadAssessmentResults(assessmentId, page);
    } catch (retryError) {
      addNotification(errorMessage(retryError, 'Could not retry this evaluation.'), 'error');
    } finally {
      setRetryingSubmissionId(null);
    }
  };

  const openSubmission = useCallback(async (submissionId) => {
    detailControllerRef.current?.abort();
    const controller = new AbortController();
    detailControllerRef.current = controller;
    setSelectedSubmission(null);
    setDetailError('');
    setDetailLoading(true);
    try {
      const response = await api.get(config.api.endpoints.results.facultySubmissionDetails, {
        params: { submission_id: submissionId },
        signal: controller.signal,
      });
      if (!controller.signal.aborted) setSelectedSubmission(response.data);
    } catch (detailRequestError) {
      if (!controller.signal.aborted) setDetailError(errorMessage(detailRequestError, 'Could not load this submission.'));
    } finally {
      if (!controller.signal.aborted) setDetailLoading(false);
    }
  }, []);

  const closeSubmission = useCallback(() => {
    detailControllerRef.current?.abort();
    detailControllerRef.current = null;
    setSelectedSubmission(null);
    setDetailError('');
    setDetailLoading(false);
  }, []);

  const submission = selectedSubmission?.submission;

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Assessment results</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Expand an assessment to see every assigned student and their result status.</p>
        </div>
        <Button variant="secondary" onClick={handleRefresh} loading={assessmentLoading} icon={RefreshCw}>
          Refresh
        </Button>
      </div>

      {assessmentError && <Alert type="error" title="Assessments could not be loaded">{assessmentError}</Alert>}

      <Card className="space-y-4">
        <div className="relative max-w-xl">
          <Input
            label="Search assessments"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Assessment title or status"
            className="pl-10"
            aria-label="Search assessments"
          />
          <Search size={16} className="pointer-events-none absolute left-3 top-[38px] text-slate-400" aria-hidden="true" />
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 pt-4 text-sm dark:border-slate-800">
          <span className="text-slate-500">{assessmentLoading ? 'Loading assessments…' : `${filteredAssessments.length} assessment${filteredAssessments.length === 1 ? '' : 's'}`}</span>
          <span className="text-slate-500">Student lists include assigned students who have not submitted.</span>
        </div>

        {assessmentLoading ? (
          <p className="py-12 text-center text-sm text-slate-500">Loading assessments…</p>
        ) : filteredAssessments.length ? (
          <div className="space-y-3">
            {filteredAssessments.map((assessment) => {
              const expanded = expandedAssessmentId === assessment.id;
              const resultSet = assessmentResults[assessment.id] || {};
              const resultPageCount = Math.max(1, Math.ceil((resultSet.count || 0) / PAGE_SIZE));
              return (
                <section key={assessment.id} className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
                  <div className="flex flex-wrap items-center gap-2 p-3 sm:p-4">
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-3 rounded-lg p-1 text-left hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:hover:bg-slate-800/60"
                      aria-expanded={expanded}
                      aria-controls={`assessment-results-${assessment.id}`}
                      onClick={() => toggleAssessment(assessment.id)}
                    >
                      <ChevronDown className={`h-5 w-5 shrink-0 text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`} aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold text-slate-900 dark:text-white">{assessment.title}</span>
                        <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                          <span>{assessment.question_count ?? 0} questions</span>
                          <span>{assessment.assignment_count ?? 0} students assigned</span>
                          <span>{assessment.total_marks ?? 0} marks</span>
                          <span>{assessment.is_timed === false ? 'Untimed' : `${assessment.duration_minutes ?? '—'} min`}</span>
                        </span>
                        <span className="mt-1 block text-xs text-slate-500">
                          Published: {formatDate(assessment.published_at)} · Assessment window: {formatDate(assessment.start_time)} – {formatDate(assessment.end_time)}
                        </span>
                      </span>
                      <Badge className={statusStyles[assessment.status] || statusStyles.closed}>
                        {(assessment.status || 'unknown').replaceAll('_', ' ')}
                      </Badge>
                    </button>
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={ArrowDownToLine}
                      loading={exportingAssessmentId === assessment.id}
                      onClick={() => handleExport(assessment.id)}
                    >
                      Export CSV
                    </Button>
                  </div>

                  {expanded && (
                    <div id={`assessment-results-${assessment.id}`} className="border-t border-slate-200 bg-slate-50/70 p-3 dark:border-slate-700 dark:bg-slate-900/40 sm:p-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                        <p className="font-medium text-slate-700 dark:text-slate-200">
                          {resultSet.count ?? assessment.assignment_count ?? 0} assigned student{(resultSet.count ?? assessment.assignment_count ?? 0) === 1 ? '' : 's'}
                        </p>
                        {resultSet.count > PAGE_SIZE && <p className="text-xs text-slate-500">Page {resultSet.page || 1} of {resultPageCount}</p>}
                      </div>

                      {resultSet.error && (
                        <Alert type="error" title="Student results could not be loaded">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <span>{resultSet.error}</span>
                            <Button size="sm" variant="secondary" onClick={() => loadAssessmentResults(assessment.id, resultSet.page || 1)}>Retry</Button>
                          </div>
                        </Alert>
                      )}

                      {resultSet.loading ? (
                        <p className="py-10 text-center text-sm text-slate-500">Loading assigned students…</p>
                      ) : resultSet.results?.length ? (
                        <div className="min-w-0 overflow-x-auto">
                          <table className="w-full min-w-[760px] text-left text-sm">
                            <thead className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                              <tr>
                                <th className="px-3 py-2">Student</th>
                                <th className="px-3 py-2">Score</th>
                                <th className="px-3 py-2">Percentage</th>
                                <th className="px-3 py-2">Tests passed</th>
                                <th className="px-3 py-2">Status</th>
                                <th className="px-3 py-2">Questions</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                              {resultSet.results.map((row) => {
                                const label = statusLabel(row);
                                const badgeKey = label === 'Not submitted' ? 'not_submitted' : row.status;
                                return (
                                  <React.Fragment key={row.assignment_id || row.id}>
                                    <tr className="text-slate-700 dark:text-slate-200">
                                      <td className="px-3 py-3">
                                        <p className="font-medium">{row.student_name || 'Unnamed student'}</p>
                                        <p className="text-xs text-slate-500">{row.student_email}</p>
                                      </td>
                                      <td className="px-3 py-3 font-medium">{Number(row.marks_obtained || 0)} / {row.total_marks}</td>
                                      <td className="px-3 py-3">{Number(row.percentage || 0).toFixed(1)}%</td>
                                      <td className="px-3 py-3">{row.passed_test_cases ?? 0} / {row.total_test_cases ?? 0}</td>
                                      <td className="px-3 py-3"><Badge className={statusStyles[badgeKey] || statusStyles.processing}>{label}</Badge></td>
                                      <td className="px-3 py-3">
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          aria-expanded={expandedResult === row.assignment_id}
                                          onClick={() => setExpandedResult((current) => current === row.assignment_id ? null : row.assignment_id)}
                                        >
                                          {expandedResult === row.assignment_id ? 'Hide' : 'View'}
                                          <Eye size={15} />
                                        </Button>
                                      </td>
                                    </tr>
                                    {expandedResult === row.assignment_id && (
                                      <tr>
                                        <td colSpan="6" className="bg-white px-3 py-4 dark:bg-slate-950/40">
                                          <div className="overflow-x-auto">
                                            <table className="w-full min-w-[800px] text-left text-sm">
                                              <thead className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                                                <tr><th className="py-2 pr-4">Question</th><th className="py-2 pr-4">Score</th><th className="py-2 pr-4">Tests passed</th><th className="py-2 pr-4">Evaluation</th><th className="py-2 pr-4">Verdict</th><th className="py-2">Code and recovery</th></tr>
                                              </thead>
                                              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                                {(row.question_results || []).map((question) => (
                                                  <tr key={question.question_id}>
                                                    <td className="py-3 pr-4">Q{question.question_order}: {question.question_title}</td>
                                                    <td className="py-3 pr-4">{question.marks_obtained} / {question.total_marks}</td>
                                                    <td className="py-3 pr-4">{question.passed_test_cases} / {question.total_test_cases}</td>
                                                    <td className="py-3 pr-4">
                                                      <Badge className={statusStyles[question.is_stale ? 'processing' : question.status] || statusStyles.processing}>
                                                        {question.is_stale ? 'Stale' : (question.status || 'unknown').replaceAll('_', ' ')}
                                                      </Badge>
                                                      {question.evaluation_generation > 1 && <p className="mt-1 text-xs text-slate-500">Retry {question.evaluation_generation - 1}</p>}
                                                    </td>
                                                    <td className="py-3 pr-4 capitalize">{(question.verdict || 'not evaluated').replaceAll('_', ' ')}</td>
                                                    <td className="py-3">
                                                      <div className="flex flex-wrap gap-2">
                                                        {question.submission_id && <Button size="sm" variant="secondary" onClick={() => openSubmission(question.submission_id)}><Eye size={15} />View code</Button>}
                                                        {question.submission_id && (question.status === 'failed' || question.is_stale) && (
                                                          <Button size="sm" variant="secondary" loading={retryingSubmissionId === question.submission_id}
                                                            onClick={() => handleRetryEvaluation(assessment.id, question.submission_id, resultSet.page || 1)}>
                                                            Retry evaluation
                                                          </Button>
                                                        )}
                                                        {!question.submission_id && '—'}
                                                      </div>
                                                      {question.is_stale && question.submission_updated_at && (
                                                        <p className="mt-1 text-xs text-amber-700 dark:text-amber-300" title={formatDate(question.submission_updated_at)}>
                                                          No update since {formatDate(question.submission_updated_at)}
                                                        </p>
                                                      )}
                                                    </td>
                                                  </tr>
                                                ))}
                                              </tbody>
                                            </table>
                                          </div>
                                        </td>
                                      </tr>
                                    )}
                                  </React.Fragment>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : !resultSet.error ? (
                        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700">
                          No students are assigned to this assessment yet.
                        </p>
                      ) : null}

                      {resultSet.count > PAGE_SIZE && !resultSet.loading && (
                        <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-3 text-sm dark:border-slate-700">
                          <span className="text-slate-500">Page {resultSet.page || 1} of {resultPageCount}</span>
                          <div className="flex gap-2">
                            <Button size="sm" variant="secondary" disabled={!resultSet.hasPrevious} onClick={() => loadAssessmentResults(assessment.id, resultSet.page - 1)}>Previous</Button>
                            <Button size="sm" variant="secondary" disabled={!resultSet.hasNext} onClick={() => loadAssessmentResults(assessment.id, resultSet.page + 1)}>Next</Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        ) : (
          <p className="py-12 text-center text-sm text-slate-500">
            {search ? 'No assessments match your search.' : 'No assessments are available yet.'}
          </p>
        )}
      </Card>

      <Modal isOpen={detailLoading || Boolean(detailError) || Boolean(selectedSubmission)} onClose={closeSubmission} title="Submission details" size="2xl">
        {detailLoading ? <p className="text-sm text-slate-500">Loading submission…</p> : detailError ? (
          <Alert type="error" title="Submission details unavailable">{detailError}</Alert>
        ) : submission ? (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h3 className="font-semibold text-slate-900 dark:text-white">{submission.question_title}</h3><p className="text-sm text-slate-500">{submission.student_name}</p></div>
              <Badge className={statusStyles[submission.status] || statusStyles.processing}>{submission.verdict_display || submission.status_display || submission.status}</Badge>
            </div>
            {submission.compilation_error && <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-rose-50 p-4 text-sm text-rose-800 dark:bg-rose-950/40 dark:text-rose-200">{submission.compilation_error}</pre>}
            <div>
              <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Submitted code</h4>
              <pre className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100"><code>{submission.source_code}</code></pre>
            </div>
            <div>
              <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Test case results</h4>
              {selectedSubmission.test_case_verdicts?.length ? (
                <div className="space-y-2">
                  {selectedSubmission.test_case_verdicts.map((testCase) => (
                    <div key={testCase.test_case_order} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
                      <span>Case {testCase.test_case_order}{testCase.is_sample ? ' · sample' : ' · hidden'}</span>
                      <span className="capitalize">{testCase.status.replaceAll('_', ' ')} · {testCase.marks_obtained} marks</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm text-slate-500">Evaluation details are not available yet.</p>}
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
};

export default FacultyResultsPage;
