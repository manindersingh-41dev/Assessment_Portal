import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, LoaderCircle, Plus, Search, SlidersHorizontal, Trash2, Upload } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client.js';
import { config } from '../../constants/config.js';
import { Badge, Card, CardDescription, CardTitle } from '../../components/Common.jsx';
import Button from '../../components/Button.jsx';
import Input from '../../components/Input.jsx';
import Modal from '../../components/Modal.jsx';
import BulkQuestionImportModal from './BulkQuestionImportModal.jsx';
import { useNotificationStore } from '../../store/notificationStore.js';
import { formatDate, getDifficultyColor } from '../../utils/formatters.js';

const PAGE_SIZE = 10;

const getApiError = (error, fallback) => {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.error === 'string') return data.error;
  if (typeof data === 'string') return data;
  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat(Infinity).find((value) => typeof value === 'string');
    if (firstError) return firstError;
  }
  return fallback;
};

const statusVariant = (status) => ({
  active: 'success',
  draft: 'warning',
  archived: 'neutral',
}[status?.toLowerCase()] || 'neutral');

const loadQuestionPages = async () => {
  let url = config.api.endpoints.questions.list;
  const allQuestions = [];
  const visitedPages = new Set();

  // The active API paginates without supporting search/filter query params.
  // Load each page so search and filters cover the full question bank.
  while (url && !visitedPages.has(url)) {
    visitedPages.add(url);
    const response = await api.get(url);
    const payload = response.data;
    allQuestions.push(...(Array.isArray(payload) ? payload : payload.results || []));
    url = Array.isArray(payload) ? null : payload.next;
  }

  return allQuestions;
};

const QuestionBankPage = () => {
  const [questions, setQuestions] = useState([]);
  const [search, setSearch] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [selectedQuestionId, setSelectedQuestionId] = useState(null);
  const [detailsRecord, setDetailsRecord] = useState(null);
  const [detailsErrorRecord, setDetailsErrorRecord] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);

  useEffect(() => {
    let isCurrent = true;
    loadQuestionPages()
      .then((allQuestions) => {
        if (isCurrent) setQuestions(allQuestions);
      })
      .catch((error) => {
        if (!isCurrent) return;
        const message = getApiError(error, 'Could not load the question bank.');
        setLoadError(message);
        addNotification(getApiError(error, 'Failed to fetch questions.'), 'error');
      })
      .finally(() => {
        if (isCurrent) setLoading(false);
      });

    return () => { isCurrent = false; };
  }, [refreshVersion, addNotification]);

  const refreshQuestions = () => {
    setLoadError('');
    setLoading(true);
    setRefreshVersion((version) => version + 1);
  };

  useEffect(() => {
    if (!selectedQuestionId) return undefined;

    let isCurrent = true;
    api.get(config.api.endpoints.questions.detail(selectedQuestionId))
      .then(({ data }) => {
        if (isCurrent) setDetailsRecord({ id: selectedQuestionId, data });
      })
      .catch((error) => {
        if (isCurrent) {
          const message = getApiError(error, 'Could not load question details.');
          setDetailsErrorRecord({ id: selectedQuestionId, message });
          addNotification(message, 'error');
        }
      });

    return () => { isCurrent = false; };
  }, [selectedQuestionId, addNotification]);

  const questionDetails = detailsRecord?.id === selectedQuestionId ? detailsRecord.data : null;
  const detailsError = detailsErrorRecord?.id === selectedQuestionId ? detailsErrorRecord.message : '';
  const detailsLoading = Boolean(selectedQuestionId) && !questionDetails && !detailsError;

  const filteredQuestions = useMemo(() => {
    const term = search.trim().toLowerCase();
    return questions.filter((question) => {
      const matchesSearch = !term || `${question.title || ''} ${question.description || ''}`.toLowerCase().includes(term);
      const matchesDifficulty = difficultyFilter === 'all' || question.difficulty?.toLowerCase() === difficultyFilter;
      const matchesStatus = statusFilter === 'all' || question.status?.toLowerCase() === statusFilter;
      return matchesSearch && matchesDifficulty && matchesStatus;
    });
  }, [questions, search, difficultyFilter, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(filteredQuestions.length / PAGE_SIZE));
  const visibleQuestions = filteredQuestions.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(config.api.endpoints.questions.delete(deleteTarget.id));
      addNotification('Question deleted successfully.', 'success');
      setDeleteTarget(null);
      refreshQuestions();
    } catch (error) {
      addNotification(getApiError(error, 'Failed to delete question.'), 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleBulkImported = (createdQuestions) => {
    setSearch('');
    setDifficultyFilter('all');
    setStatusFilter('all');
    setPage(1);
    refreshQuestions();
    addNotification(`${createdQuestions.length} questions and their test cases were added to the question bank.`, 'success');
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-600 dark:text-primary-400">Faculty workspace</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Question bank</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Search, review, and manage your programming questions.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setBulkImportOpen(true)} icon={Upload}>Bulk upload</Button>
          <Button onClick={() => navigate('/faculty/questions/create')} icon={Plus}>Create question</Button>
        </div>
      </div>

      <Card className="p-4 sm:p-5">
        <div className="grid gap-3 xl:grid-cols-[minmax(16rem,1fr)_12rem_12rem]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <Input
              aria-label="Search questions"
              placeholder="Search title or description"
              value={search}
              onChange={(event) => { setSearch(event.target.value); setPage(1); }}
              className="pl-9"
            />
          </div>
          <Input
            as="select"
            label="Difficulty"
            value={difficultyFilter}
            onChange={(event) => { setDifficultyFilter(event.target.value); setPage(1); }}
          >
            <option value="all">All difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </Input>
          <Input
            as="select"
            label="Status"
            value={statusFilter}
            onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}
          >
            <option value="all">All statuses</option>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </Input>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div>
            <CardTitle>Questions</CardTitle>
            <CardDescription>{filteredQuestions.length} {filteredQuestions.length === 1 ? 'question' : 'questions'} found</CardDescription>
          </div>
          <SlidersHorizontal className="h-5 w-5 text-slate-400" aria-hidden="true" />
        </div>

        {loading ? (
          <div className="flex min-h-56 items-center justify-center gap-3 text-sm text-slate-500" role="status">
            <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" /> Loading questions…
          </div>
        ) : loadError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-danger-600 dark:text-danger-400">{loadError}</p>
            <Button className="mt-4" variant="secondary" onClick={refreshQuestions}>Try again</Button>
          </div>
        ) : visibleQuestions.length === 0 ? (
          <div className="px-6 py-14 text-center">
            <p className="font-semibold text-slate-900 dark:text-white">No questions found</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Try changing your search or filters, or create a question.</p>
          </div>
        ) : (
          <>
            <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950/50 dark:text-slate-400">
                  <tr>
                    <th scope="col" className="px-5 py-3 font-semibold">Question</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Topic</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Difficulty</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Marks</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Created</th>
                    <th scope="col" className="px-5 py-3 text-right font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {visibleQuestions.map((question) => (
                    <tr key={question.id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                      <td className="max-w-sm px-5 py-4">
                        <p className="truncate font-semibold text-slate-900 dark:text-white" title={question.title}>{question.title}</p>
                        {question.description && <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">{question.description}</p>}
                      </td>
                      <td className="px-4 py-4">{question.topic ? <Badge variant="neutral">{question.topic}</Badge> : <span className="text-slate-400">—</span>}</td>
                      <td className="px-4 py-4"><Badge variant={getDifficultyColor(question.difficulty)}>{question.difficulty || '—'}</Badge></td>
                      <td className="px-4 py-4 text-slate-700 dark:text-slate-300">{question.total_marks ?? '—'}</td>
                      <td className="px-4 py-4"><Badge variant={statusVariant(question.status)}>{question.status || 'Unknown'}</Badge></td>
                      <td className="whitespace-nowrap px-4 py-4 text-slate-600 dark:text-slate-400">{question.created_at ? formatDate(question.created_at) : '—'}</td>
                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="ghost" aria-label={`View ${question.title}`} onClick={() => setSelectedQuestionId(question.id)} icon={Eye}>View</Button>
                          <Button size="sm" variant="secondary" onClick={() => navigate(`/faculty/questions/${question.id}/edit`)}>Edit</Button>
                          <Button
                            size="sm"
                            variant="danger"
                            aria-label={`Delete ${question.title}`}
                            title={question.has_submissions ? 'Questions with submissions cannot be deleted' : question.status?.toLowerCase() === 'draft' ? 'Delete question' : 'Only draft questions can be deleted'}
                            disabled={question.status?.toLowerCase() !== 'draft' || question.has_submissions}
                            onClick={() => setDeleteTarget(question)}
                            icon={Trash2}
                          >Delete</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-3 border-t border-slate-100 px-5 py-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">Page {page} of {pageCount}</p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} icon={ChevronLeft}>Previous</Button>
                <Button size="sm" variant="outline" disabled={page >= pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>
                  Next <ChevronRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>

      <Modal
        isOpen={Boolean(selectedQuestionId)}
        onClose={() => setSelectedQuestionId(null)}
        title={questionDetails?.title || 'Question details'}
        size="2xl"
        footer={questionDetails && <Button onClick={() => navigate(`/faculty/questions/${questionDetails.id}/edit`)}>Edit question</Button>}
      >
        {detailsLoading ? (
          <div className="flex items-center justify-center gap-3 py-10 text-sm text-slate-500"><LoaderCircle className="h-5 w-5 animate-spin" /> Loading details…</div>
        ) : questionDetails ? (
          <div className="space-y-5">
            <div className="flex flex-wrap gap-2">
              <Badge variant={getDifficultyColor(questionDetails.difficulty)}>{questionDetails.difficulty}</Badge>
              <Badge variant={statusVariant(questionDetails.status)}>{questionDetails.status}</Badge>
              <Badge variant="neutral">{questionDetails.total_marks} marks</Badge>
              <Badge variant="neutral">{questionDetails.language?.toUpperCase() || 'C'}</Badge>
            </div>
            <section>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Problem statement</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-300">{questionDetails.description || 'No description provided.'}</p>
            </section>
            <div className="grid gap-4 sm:grid-cols-2">
              <section>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Input format</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-400">{questionDetails.input_format || '—'}</p>
              </section>
              <section>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Output format</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-400">{questionDetails.output_format || '—'}</p>
              </section>
            </div>
            <section>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Constraints</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-400">{questionDetails.constraints || '—'}</p>
            </section>
            <div className="grid gap-4 sm:grid-cols-2">
              <section>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Sample input</h3>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-950 dark:text-slate-200">{questionDetails.sample_input || '—'}</pre>
              </section>
              <section>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Sample output</h3>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-950 dark:text-slate-200">{questionDetails.sample_output || '—'}</pre>
              </section>
            </div>
            {questionDetails.sample_explanation && <section><h3 className="text-sm font-semibold text-slate-900 dark:text-white">Sample explanation</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-400">{questionDetails.sample_explanation}</p></section>}
            <div className="grid gap-4 sm:grid-cols-2">
              <div><h3 className="text-sm font-semibold text-slate-900 dark:text-white">Time limit</h3><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{questionDetails.time_limit_seconds ?? '—'} seconds</p></div>
              <div><h3 className="text-sm font-semibold text-slate-900 dark:text-white">Created</h3><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{questionDetails.created_at ? formatDate(questionDetails.created_at, 'long') : '—'}</p></div>
            </div>
            {Array.isArray(questionDetails.test_cases) && (
              <section>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Test cases ({questionDetails.test_cases.length})</h3>
                {questionDetails.test_cases.length ? (
                  <div className="mt-3 space-y-3">
                    {questionDetails.test_cases.map((testCase, index) => (
                      <div key={testCase.id || index} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-slate-800 dark:text-slate-200">Test case {testCase.order || index + 1}</span>
                          <div className="flex gap-2"><Badge variant={testCase.is_sample ? 'info' : 'neutral'}>{testCase.is_sample ? 'Sample' : 'Hidden'}</Badge><Badge variant="neutral">{testCase.marks} marks</Badge></div>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div><p className="mb-1 text-xs font-semibold uppercase text-slate-500">Input</p><pre className="overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-950 dark:text-slate-200">{testCase.input}</pre></div>
                          <div><p className="mb-1 text-xs font-semibold uppercase text-slate-500">Expected output</p><pre className="overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-950 dark:text-slate-200">{testCase.expected_output}</pre></div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No test cases have been added.</p>}
              </section>
            )}
          </div>
        ) : detailsError ? (
          <p className="py-8 text-sm text-danger-600 dark:text-danger-400">{detailsError}</p>
        ) : (
          <p className="py-8 text-sm text-slate-500 dark:text-slate-400">Question details are unavailable.</p>
        )}
      </Modal>

      <Modal
        isOpen={Boolean(deleteTarget)}
        onClose={() => !deleting && setDeleteTarget(null)}
        title="Delete question?"
        size="sm"
        footer={(
          <>
            <Button variant="secondary" disabled={deleting} onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" loading={deleting} onClick={handleDelete}>Delete</Button>
          </>
        )}
      >
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">This will permanently delete <strong className="text-slate-900 dark:text-white">{deleteTarget?.title}</strong> and its associated test cases.</p>
      </Modal>

      <BulkQuestionImportModal
        isOpen={bulkImportOpen}
        onClose={() => setBulkImportOpen(false)}
        onImported={handleBulkImported}
      />
    </div>
  );
};

export default QuestionBankPage;
