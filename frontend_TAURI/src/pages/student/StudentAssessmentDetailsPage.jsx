import React, { useEffect, useState } from 'react';
import { ArrowLeft, CalendarClock, CheckCircle2, Clock3, FileText, Info, Play } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../../components/Button';
import { Alert, Badge, Card } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';
import { isChildrenDay } from '../../utils/isChildrenDay.js';

const endpoints = config.api.endpoints;
const completedAssignmentStates = ['submitted', 'graded', 'expired'];

const asList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const dateLabel = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not scheduled' : date.toLocaleString();
};

const StudentAssessmentDetailsPage = () => {
  const [assessment, setAssessment] = useState(null);
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [now, setNow] = useState(0);
  const { id } = useParams();
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);

  const loadData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError('');
    const [assessmentResult, assignmentsResult] = await Promise.allSettled([
      api.get(endpoints.assessments.detail(id)),
      api.get(endpoints.assessments.myAssignments, { params: { page_size: 100 } }),
    ]);
    if (assessmentResult.status === 'rejected') {
      const message = assessmentResult.reason?.response?.data?.detail || 'Could not load this assessment.';
      setError(message);
      addNotification(message, 'error');
      setAssessment(null);
      setLoading(false);
      return;
    }

    const current = assessmentResult.value.data?.assessment || assessmentResult.value.data;
    setAssessment(current);
    if (assignmentsResult.status === 'fulfilled') {
      const ownAssignment = asList(assignmentsResult.value.data)
        .find((item) => String(item.assessment?.id || item.assessment) === String(id));
      setAssignment(ownAssignment || null);
    } else {
      setAssignment(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get(endpoints.assessments.detail(id)),
      api.get(endpoints.assessments.myAssignments, { params: { page_size: 100 } }),
    ]).then(([assessmentResult, assignmentsResult]) => {
      if (!active) return;
      if (assessmentResult.status === 'rejected') {
        const message = assessmentResult.reason?.response?.data?.detail || 'Could not load this assessment.';
        setError(message);
        setAssessment(null);
        addNotification(message, 'error');
        return;
      }
      const current = assessmentResult.value.data?.assessment || assessmentResult.value.data;
      setAssessment(current);
      if (assignmentsResult.status === 'fulfilled') {
        const ownAssignment = asList(assignmentsResult.value.data)
          .find((item) => String(item.assessment?.id || item.assessment) === String(id));
        setAssignment(ownAssignment || null);
      } else {
        setAssignment(null);
      }
      setError('');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [addNotification, id]);

  useEffect(() => {
    const updateNow = () => setNow(Date.now());
    const firstUpdate = window.setTimeout(updateNow, 0);
    const interval = window.setInterval(updateNow, 60_000);
    return () => {
      window.clearTimeout(firstUpdate);
      window.clearInterval(interval);
    };
  }, []);

  if (loading) return <div className="p-8 text-center text-sm text-slate-500">Loading assessment…</div>;
  if (!assessment) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <Button variant="ghost" onClick={() => navigate('/student/assessments')}><ArrowLeft size={16} />My assessments</Button>
        <Alert type="error" title="Assessment unavailable">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error || 'This assessment could not be found or is no longer assigned to you.'}</span>
            <Button variant="secondary" size="sm" onClick={() => loadData()}>Try again</Button>
          </div>
        </Alert>
      </div>
    );
  }

  const start = new Date(assessment.start_time).getTime();
  const end = new Date(assessment.end_time).getTime();
  const isSubmitted = completedAssignmentStates.includes(assignment?.status);
  const canResumeUntimed = assignment?.status === 'started' && assessment.is_timed === false;
  const isUpcoming = Number.isFinite(start) && now < start;
  const isPastEnd = Number.isFinite(end) && now > end && !canResumeUntimed;
  const isActive = !isSubmitted && !isUpcoming && !isPastEnd;
  const status = isSubmitted || isPastEnd ? 'Completed' : isUpcoming ? 'Upcoming' : 'Active';
  const statusVariant = status === 'Active' ? 'success' : status === 'Upcoming' ? 'info' : 'neutral';
  const questionCount = assessment.question_count
    ?? assessment.assessment_questions?.length
    ?? assessment.questions?.length
    ?? 0;
  const startAction = assignment?.status === 'started' ? 'Continue assessment' : 'Start assessment';
  const childrenDay = isChildrenDay();

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <Button variant="ghost" onClick={() => navigate('/student/assessments')}><ArrowLeft size={16} />My assessments</Button>

      {error && <Alert type="warning">Assessment details loaded with a warning: {error}</Alert>}

      <Card className="overflow-hidden p-0">
        <div className="border-b border-slate-100 p-5 sm:p-8 dark:border-slate-800">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl">
              <div className="mb-3"><Badge variant={statusVariant}>{status}</Badge></div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white sm:text-3xl">{assessment.title}</h1>
              {assessment.description && (
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">{assessment.description}</p>
              )}
            </div>
            <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800">
              <p className="font-semibold text-slate-900 dark:text-white">Your assignment</p>
              <p className="mt-1 capitalize text-slate-600 dark:text-slate-300">{assignment?.status || 'Assigned'}</p>
              {assignment?.due_at && <p className="mt-2 text-xs text-slate-500">Personal deadline: {dateLabel(assignment.due_at)}</p>}
            </div>
          </div>
        </div>

        <div className="grid gap-px bg-slate-100 sm:grid-cols-2 lg:grid-cols-4 dark:bg-slate-800">
          <div className="bg-white p-5 dark:bg-slate-900"><p className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500"><CalendarClock size={14} />Starts</p><p className="mt-2 text-sm font-semibold">{dateLabel(assessment.start_time)}</p></div>
          <div className="bg-white p-5 dark:bg-slate-900"><p className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500"><CalendarClock size={14} />Ends</p><p className="mt-2 text-sm font-semibold">{dateLabel(assessment.end_time)}</p></div>
          <div className="bg-white p-5 dark:bg-slate-900"><p className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500"><Clock3 size={14} />Time limit</p><p className="mt-2 text-sm font-semibold">{assessment.is_timed === false ? 'No time limit after starting' : `${assessment.duration_minutes} minutes`}</p></div>
          <div className="bg-white p-5 dark:bg-slate-900"><p className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500"><CheckCircle2 size={14} />Points</p><p className="mt-2 text-sm font-semibold">{questionCount} questions · {assessment.total_marks} marks</p></div>
        </div>

        <div className="grid gap-6 p-5 sm:p-8 lg:grid-cols-[minmax(0,1fr)_300px]">
          <section>
            <div className="flex items-center gap-2"><FileText size={18} className="text-primary-600" /><h2 className="text-lg font-semibold">Instructions</h2></div>
            {assessment.instructions ? (
              <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700 dark:text-slate-300">{assessment.instructions}</div>
            ) : (
              <div className="mt-3 rounded-lg bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {assessment.is_timed === false
                  ? 'No additional instructions were provided. Start before the assessment window closes; your saved work will be here when you return.'
                  : 'No additional instructions were provided. Read each question carefully and submit your work before the assessment closes.'}
              </div>
            )}
          </section>

          <aside className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <div className="flex gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Info size={16} className="mt-0.5 shrink-0 text-primary-600" />Before you begin</div>
            <ul className="mt-3 space-y-2 pl-5 text-sm text-slate-600 dark:text-slate-300">
              <li className="list-disc">Check the start and end times shown above.</li>
              <li className="list-disc">{assessment.is_timed === false ? 'There is no completion timer after you start.' : 'Your timer begins when you start the assessment.'}</li>
              <li className="list-disc">{assessment.is_timed === false ? 'Your work is autosaved; you can leave and return later.' : 'Your work is autosaved, but the timer keeps running while you are away.'}</li>
            </ul>
          </aside>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-5 sm:px-8 dark:border-slate-800">
          <p className="text-xs text-slate-500">
            {isSubmitted ? 'Your submission has been recorded.' : isUpcoming ? `This assessment opens ${dateLabel(assessment.start_time)}.` : canResumeUntimed ? 'The scheduled window has closed, but you can resume your untimed attempt.' : isPastEnd ? 'The assessment window has closed.' : 'You can start while the assessment window is open.'}
          </p>
          <Button size="lg" disabled={!isActive || (!assignment && !childrenDay)} onClick={() => navigate(childrenDay ? '/childrens-day' : `/assessment/${assessment.id}`)}>
            <Play size={16} />{isSubmitted ? 'Submitted' : isUpcoming ? 'Not open yet' : isPastEnd ? 'Assessment closed' : startAction}
          </Button>
        </div>
      </Card>
      <p className="text-center text-xs text-slate-500">The coding workspace opens when you start. Submission and grading details will be available in a later module.</p>
    </div>
  );
};

export default StudentAssessmentDetailsPage;
