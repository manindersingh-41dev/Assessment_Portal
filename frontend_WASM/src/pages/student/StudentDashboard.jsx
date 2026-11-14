import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, BarChart3, CalendarClock, CheckCircle2, Clock3, ClipboardList, RefreshCw } from 'lucide-react';
import { Button } from '../../components/Button';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import { useAuthStore } from '../../store/authStore';
import api from '../../api/client';
import { config } from '../../constants/config';
import { isChildrenDay } from '../../utils/isChildrenDay.js';

const endpoints = config.api.endpoints;
const tabs = [
  { key: 'all', label: 'All assessments', path: '/student/assessments' },
  { key: 'active', label: 'Active', path: '/student/assessments/active' },
  { key: 'upcoming', label: 'Upcoming', path: '/student/assessments/upcoming' },
  { key: 'completed', label: 'Completed', path: '/student/assessments/completed' },
];

const asList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const assessmentCategory = (assessment, now) => {
  const assignmentStatus = assessment.assignment?.status;
  if (['submitted', 'graded', 'expired'].includes(assignmentStatus)) return 'completed';
  const start = new Date(assessment.start_time).getTime();
  if (Number.isFinite(start) && now < start) return 'upcoming';
  const deadlines = [assessment.end_time, assessment.assignment?.due_at]
    .map((value) => new Date(value).getTime())
    .filter(Number.isFinite);
  if (deadlines.length && now > Math.min(...deadlines)) return 'completed';
  return 'active';
};

const dateLabel = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not scheduled' : date.toLocaleString();
};

const statusVariant = (category) => ({ active: 'success', upcoming: 'info', completed: 'neutral' }[category] || 'neutral');

const AssessmentCard = ({ assessment, category, onOpen }) => {
  const actionText = category === 'active'
    ? assessment.assignment?.status === 'started' ? 'Continue assessment' : 'Start assessment'
    : category === 'upcoming' ? 'View details' : 'Review details';

  return (
    <Card className="flex h-full flex-col transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="truncate text-base">{assessment.title}</CardTitle>
          <CardDescription className="mt-2 line-clamp-2 min-h-10">
            {assessment.description || 'No description provided.'}
          </CardDescription>
        </div>
        <Badge variant={statusVariant(category)} className="capitalize">{category}</Badge>
      </div>
      <div className="my-5 space-y-3 border-y border-slate-100 py-4 text-sm dark:border-slate-800">
        <div className="flex items-center justify-between gap-3 text-slate-600 dark:text-slate-300">
          <span className="inline-flex items-center gap-2"><ClipboardList size={15} />Questions</span>
          <span className="font-semibold text-slate-900 dark:text-white">
            {assessment.question_count ?? assessment.assessment_questions?.length ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3 text-slate-600 dark:text-slate-300">
          <span className="inline-flex items-center gap-2"><CheckCircle2 size={15} />Total marks</span>
          <span className="font-semibold text-slate-900 dark:text-white">{assessment.total_marks}</span>
        </div>
        <div className="flex items-center justify-between gap-3 text-slate-600 dark:text-slate-300">
          <span className="inline-flex items-center gap-2"><Clock3 size={15} />Time limit</span>
          <span className="font-semibold text-slate-900 dark:text-white">{assessment.is_timed === false ? 'None' : `${assessment.duration_minutes} min`}</span>
        </div>
        <div className="flex items-start justify-between gap-3 text-xs text-slate-500">
          <span className="inline-flex items-center gap-2"><CalendarClock size={15} />{category === 'upcoming' ? 'Starts' : 'Ends'}</span>
          <span className="text-right">{dateLabel(category === 'upcoming' ? assessment.start_time : assessment.end_time)}</span>
        </div>
      </div>
      <Button className="mt-auto" variant={category === 'active' ? 'primary' : 'secondary'} fullWidth onClick={onOpen}>
        {actionText}<ArrowRight size={16} />
      </Button>
    </Card>
  );
};

const StudentDashboard = ({ filter = 'all' }) => {
  const [assessments, setAssessments] = useState([]);
  const [recentResults, setRecentResults] = useState([]);
  const [resultsLoading, setResultsLoading] = useState(true);
  const [resultsRefreshKey, setResultsRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [now, setNow] = useState(0);
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);

  const loadDashboard = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError('');
    const [assessmentsResult, assignmentsResult] = await Promise.allSettled([
      api.get(endpoints.assessments.list, { params: { page_size: 100 } }),
      api.get(endpoints.assessments.myAssignments, { params: { page_size: 100 } }),
    ]);

    if (assessmentsResult.status === 'rejected') {
      const message = assessmentsResult.reason?.response?.data?.detail || 'Could not load your assessments.';
      setError(message);
      addNotification(message, 'error');
      setAssessments([]);
      setLoading(false);
      return;
    }

    const assessmentRows = asList(assessmentsResult.value.data);
    const assignmentRows = assignmentsResult.status === 'fulfilled'
      ? asList(assignmentsResult.value.data)
      : [];
    if (assignmentsResult.status === 'rejected') {
      addNotification('Assessment progress could not be loaded; dates are used to show status.', 'warning');
    }
    const assignmentByAssessment = new Map(
      assignmentRows.map((assignment) => [String(assignment.assessment?.id || assignment.assessment), assignment]),
    );
    setAssessments(assessmentRows.map((assessment) => ({
      ...assessment,
      assignment: assignmentByAssessment.get(String(assessment.id)),
    })));
    setError('');
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get(endpoints.assessments.list, { params: { page_size: 100 } }),
      api.get(endpoints.assessments.myAssignments, { params: { page_size: 100 } }),
    ]).then(([assessmentsResult, assignmentsResult]) => {
      if (!active) return;
      if (assessmentsResult.status === 'rejected') {
        const message = assessmentsResult.reason?.response?.data?.detail || 'Could not load your assessments.';
        setError(message);
        addNotification(message, 'error');
        setAssessments([]);
        return;
      }
      const assessmentRows = asList(assessmentsResult.value.data);
      const assignmentRows = assignmentsResult.status === 'fulfilled'
        ? asList(assignmentsResult.value.data)
        : [];
      if (assignmentsResult.status === 'rejected') {
        addNotification('Assessment progress could not be loaded; dates are used to show status.', 'warning');
      }
      const assignmentByAssessment = new Map(
        assignmentRows.map((assignment) => [String(assignment.assessment?.id || assignment.assessment), assignment]),
      );
      setAssessments(assessmentRows.map((assessment) => ({
        ...assessment,
        assignment: assignmentByAssessment.get(String(assessment.id)),
      })));
      setError('');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [addNotification]);

  useEffect(() => {
    const controller = new AbortController();
    setResultsLoading(true);
    api.get(endpoints.results.studentResults, {
      params: { page_size: 3 },
      signal: controller.signal,
    }).then((response) => {
      setRecentResults(asList(response.data));
    }).catch((requestError) => {
      if (!controller.signal.aborted) {
        addNotification(requestError.response?.data?.detail || 'Recent results could not be loaded.', 'warning');
      }
    }).finally(() => {
      if (!controller.signal.aborted) setResultsLoading(false);
    });
    return () => controller.abort();
  }, [addNotification, resultsRefreshKey]);

  useEffect(() => {
    const updateNow = () => setNow(Date.now());
    const firstUpdate = window.setTimeout(updateNow, 0);
    const interval = window.setInterval(updateNow, 60_000);
    return () => {
      window.clearTimeout(firstUpdate);
      window.clearInterval(interval);
    };
  }, []);

  const categorized = useMemo(() => assessments.reduce((groups, assessment) => {
    const category = assessmentCategory(assessment, now);
    groups[category].push(assessment);
    return groups;
  }, { active: [], upcoming: [], completed: [] }), [assessments, now]);

  const visibleAssessments = filter === 'all'
    ? []
    : categorized[filter] || [];

  const openAssessment = (assessment, category) => {
    if (category === 'active' && isChildrenDay()) navigate('/childrens-day');
    else if (category === 'active') navigate(`/assessment/${assessment.id}`);
    else navigate(`/student/assessments/${assessment.id}`);
  };

  const renderCards = (items, category, limit = Infinity) => (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.slice(0, limit).map((assessment) => (
        <AssessmentCard key={assessment.id} assessment={assessment} category={category}
          onOpen={() => openAssessment(assessment, category)} />
      ))}
      {items.length === 0 && (
        <div className="col-span-full rounded-xl border border-dashed border-slate-300 px-5 py-10 text-center text-sm text-slate-500 dark:border-slate-700">
          No {category} assessments right now.
        </div>
      )}
    </div>
  );

  const pageTitle = filter === 'all' ? 'My assessments' : `${filter[0].toUpperCase()}${filter.slice(1)} assessments`;

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome back{user?.first_name ? `, ${user.first_name}` : ''}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{pageTitle} and your assessment schedule.</p>
        </div>
        <Button variant="secondary" onClick={() => { loadDashboard(); setResultsRefreshKey((current) => current + 1); }} loading={loading} icon={RefreshCw}>Refresh</Button>
      </div>

      <div className="flex gap-2 overflow-x-auto border-b border-slate-200 pb-2 dark:border-slate-800" role="tablist" aria-label="Assessment categories">
        {tabs.map((tab) => (
          <button key={tab.key} type="button" role="tab" aria-selected={filter === tab.key}
            onClick={() => navigate(tab.path)}
            className={`shrink-0 rounded-lg px-3.5 py-2 text-sm font-semibold transition ${filter === tab.key
              ? 'bg-primary-50 text-primary-700 dark:bg-primary-950/50 dark:text-primary-300'
              : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
            {tab.label}
            {tab.key !== 'all' && <span className="ml-2 text-xs opacity-70">{categorized[tab.key].length}</span>}
          </button>
        ))}
      </div>

      {error && <Alert type="error" title="Assessments could not be loaded">{error}</Alert>}

      {loading ? (
        <div className="py-20 text-center text-sm text-slate-500">Loading your assessments…</div>
      ) : filter === 'all' ? (
        <div className="space-y-8">
          {(['active', 'upcoming', 'completed']).map((category) => (
            <section key={category} className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div><h2 className="text-lg font-bold capitalize text-slate-900 dark:text-white">{category} assessments</h2>
                  <p className="text-sm text-slate-500">{categorized[category].length} assigned</p></div>
                {categorized[category].length > 3 && (
                  <Button size="sm" variant="ghost" onClick={() => navigate(`/student/assessments/${category}`)}>View all</Button>
                )}
              </div>
              {renderCards(categorized[category], category, 3)}
            </section>
          ))}
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="rounded-xl bg-primary-50 p-2.5 text-primary-700 dark:bg-primary-950 dark:text-primary-300"><BarChart3 size={20} /></span>
                <div><CardTitle className="text-base">Recent results</CardTitle><CardDescription>Latest submitted assessment scorecards.</CardDescription></div>
              </div>
              <Button size="sm" variant="ghost" onClick={() => navigate('/student/results')}>All results<ArrowRight size={15} /></Button>
            </div>
            {resultsLoading ? <p className="py-4 text-sm text-slate-500">Loading scorecards…</p> : recentResults.length ? (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {recentResults.map((result) => (
                  <div key={result.assignment_id || result.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                    <div><p className="font-medium text-slate-900 dark:text-white">{result.assessment_title}</p><p className="text-xs text-slate-500">{result.marks_obtained} / {result.total_marks} marks · {Number(result.percentage || 0).toFixed(1)}%</p></div>
                    <Badge className="capitalize">{(result.status || 'processing').replaceAll('_', ' ')}</Badge>
                  </div>
                ))}
              </div>
            ) : <p className="py-4 text-sm text-slate-500">No submitted scorecards yet.</p>}
          </Card>
          <Card className="border-sky-200 bg-sky-50/60 dark:border-sky-900 dark:bg-sky-950/20">
            <CardTitle className="text-base">Need help?</CardTitle>
            <CardDescription>Open an assessment to read its instructions. Your coding workspace opens when you start an active assessment.</CardDescription>
          </Card>
        </div>
      ) : (
        <section className="space-y-4">
          <div><h2 className="text-lg font-bold capitalize text-slate-900 dark:text-white">{filter} assessments</h2>
            <p className="text-sm text-slate-500">{visibleAssessments.length} assigned</p></div>
          {renderCards(visibleAssessments, filter)}
        </section>
      )}
    </div>
  );
};

export default StudentDashboard;
