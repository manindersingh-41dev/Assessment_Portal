import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, CalendarClock, ClipboardList, Clock3, Pencil, Users } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../../components/Button';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const endpoints = config.api.endpoints;

const statusVariant = (status) => ({
  active: 'success',
  scheduled: 'info',
  draft: 'neutral',
  closed: 'warning',
  archived: 'neutral',
}[status] || 'neutral');

const dateLabel = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not scheduled' : date.toLocaleString();
};

const AssessmentDetailsPage = () => {
  const [assessment, setAssessment] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [retryingNotificationId, setRetryingNotificationId] = useState(null);
  const [loadError, setLoadError] = useState('');
  const { id } = useParams();
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);

  const fetchAssessment = useCallback(async () => {
    try {
      const [assessmentResponse, assignmentResponse] = await Promise.all([
        api.get(endpoints.assessments.detail(id)),
        api.get(endpoints.assessments.assignments(id)),
      ]);
      const current = assessmentResponse.data?.assessment || assessmentResponse.data;
      setAssessment(current);
      setLoadError('');
      const assignmentData = assignmentResponse.data?.assignments || assignmentResponse.data?.results || [];
      setAssignments(Array.isArray(assignmentData) ? assignmentData : []);
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to load assessment details.';
      setLoadError(message);
      addNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addNotification, id]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get(endpoints.assessments.detail(id)),
      api.get(endpoints.assessments.assignments(id)),
    ])
      .then(([assessmentResponse, assignmentResponse]) => {
        if (!active) return;
        const current = assessmentResponse.data?.assessment || assessmentResponse.data;
        setAssessment(current);
        const assignmentData = assignmentResponse.data?.assignments || assignmentResponse.data?.results || [];
        setAssignments(Array.isArray(assignmentData) ? assignmentData : []);
        setLoadError('');
      })
      .catch((error) => {
        if (!active) return;
        const message = error.response?.data?.detail || 'Failed to load assessment details.';
        setLoadError(message);
        addNotification(message, 'error');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [addNotification, id]);

  const retryFetchAssessment = () => {
    setLoading(true);
    fetchAssessment();
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      const response = await api.post(endpoints.assessments.publish(id));
      const updated = response.data?.assessment || response.data;
      setAssessment((current) => ({ ...current, ...updated, is_published: true, status: 'active' }));
      addNotification('Assessment published.', 'success');
    } catch (error) {
      addNotification(error.response?.data?.detail || error.response?.data?.error || 'Could not publish the assessment.', 'error');
    } finally {
      setPublishing(false);
    }
  };

  const retryEmail = async (assignmentId, notificationId) => {
    setRetryingNotificationId(notificationId);
    try {
      await api.post(endpoints.assessments.retryNotification(assignmentId, notificationId));
      addNotification('Email retry queued.', 'success');
      await fetchAssessment();
    } catch (error) {
      addNotification(error.response?.data?.error || 'Could not retry this email.', 'error');
    } finally {
      setRetryingNotificationId(null);
    }
  };

  if (loading) return <div className="p-8 text-center text-sm text-slate-500">Loading assessment…</div>;
  if (loadError && !assessment) {
    return (
      <div className="space-y-4 p-4 sm:p-6">
        <Button variant="ghost" onClick={() => navigate('/faculty/assessments')}><ArrowLeft size={16} />Assessments</Button>
        <Alert type="error" title="Assessment could not be loaded">
          <div className="flex flex-wrap items-center justify-between gap-3"><span>{loadError}</span>
            <Button variant="secondary" size="sm" onClick={retryFetchAssessment}>Try again</Button>
          </div>
        </Alert>
      </div>
    );
  }
  if (!assessment) return <div className="p-8 text-center text-slate-500">Assessment not found.</div>;

  const questions = assessment.assessment_questions || assessment.questions || [];

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="sm" aria-label="Back to assessments" onClick={() => navigate('/faculty/assessments')}>
            <ArrowLeft size={17} />
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{assessment.title}</h1>
              <Badge variant={statusVariant(assessment.status)}>{assessment.status || 'draft'}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Assessment details and assigned students</p>
          </div>
        </div>
        <div className="flex gap-2">
          {!assessment.is_published && (
            <Button variant="success" loading={publishing} onClick={handlePublish}>Publish</Button>
          )}
          <Button variant="secondary" onClick={() => navigate(`/faculty/assessments/${id}/edit`)} icon={Pencil}>Edit</Button>
        </div>
      </div>

      {loadError && <Alert type="warning">Some assessment information could not be refreshed: {loadError}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="flex items-center gap-3">
          <span className="rounded-lg bg-primary-50 p-2.5 text-primary-700 dark:bg-primary-950/60 dark:text-primary-300"><ClipboardList size={19} /></span>
          <div><p className="text-xs text-slate-500">Questions</p><p className="text-xl font-bold">{assessment.question_count ?? questions.length}</p></div>
        </Card>
        <Card className="flex items-center gap-3">
          <span className="rounded-lg bg-sky-50 p-2.5 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300"><Clock3 size={19} /></span>
          <div><p className="text-xs text-slate-500">Time limit</p><p className="text-xl font-bold">{assessment.is_timed === false ? 'None' : `${assessment.duration_minutes} min`}</p></div>
        </Card>
        <Card className="flex items-center gap-3">
          <span className="rounded-lg bg-emerald-50 p-2.5 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"><Users size={19} /></span>
          <div><p className="text-xs text-slate-500">Assigned students</p><p className="text-xl font-bold">{assessment.assignment_count ?? assignments.length}</p></div>
        </Card>
        <Card className="flex items-center gap-3">
          <span className="rounded-lg bg-amber-50 p-2.5 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"><CalendarClock size={19} /></span>
          <div><p className="text-xs text-slate-500">Total marks</p><p className="text-xl font-bold">{assessment.total_marks}</p></div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardTitle>Assessment information</CardTitle>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Starts</p><p className="mt-1 text-sm">{dateLabel(assessment.start_time)}</p></div>
              <div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Ends</p><p className="mt-1 text-sm">{dateLabel(assessment.end_time)}</p></div>
              <div className="sm:col-span-2"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Description</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{assessment.description || 'No description provided.'}</p></div>
              <div className="sm:col-span-2"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Instructions</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{assessment.instructions || 'No instructions provided.'}</p></div>
            </div>
          </Card>

          <Card>
            <div className="mb-4 flex items-end justify-between gap-3">
              <div><CardTitle>Questions</CardTitle><CardDescription>Order and marks used in this assessment.</CardDescription></div>
              <Button variant="outline" size="sm" onClick={() => navigate(`/faculty/assessments/${id}/edit`)}>Edit questions</Button>
            </div>
            <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
              <table className="w-full min-w-[500px] text-left text-sm">
                <thead><tr className="border-y border-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
                  <th className="px-3 py-3">#</th><th className="px-3 py-3">Question</th><th className="px-3 py-3">Difficulty</th><th className="px-3 py-3 text-right">Marks</th>
                </tr></thead>
                <tbody>
                  {questions.map((link, index) => {
                    const question = link.question && typeof link.question === 'object' ? link.question : {};
                    return (
                      <tr key={link.id || link.question || index} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                        <td className="px-3 py-3 text-slate-500">{link.order || index + 1}</td>
                        <td className="px-3 py-3 font-medium">{link.question_title || question.title || link.title || 'Question'}</td>
                        <td className="px-3 py-3 capitalize text-slate-500">{link.question_difficulty || question.difficulty || link.difficulty || '—'}</td>
                        <td className="px-3 py-3 text-right">{link.marks}</td>
                      </tr>
                    );
                  })}
                  {questions.length === 0 && <tr><td colSpan="4" className="px-3 py-10 text-center text-slate-500">No questions have been added.</td></tr>}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <Card className="h-fit">
          <CardTitle>Assigned students</CardTitle>
          <CardDescription>{assignments.length} student{assignments.length === 1 ? '' : 's'} assigned</CardDescription>
          <div className="mt-4 max-h-[28rem] space-y-2 overflow-y-auto">
            {assignments.map((assignment) => {
              const notifications = assignment.email_notifications || [];
              return (
                <div key={assignment.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-white">
                    {assignment.student_name || assignment.student_email || assignment.student?.email || 'Student'}
                  </p>
                  {(assignment.student_email || assignment.student?.email) && (
                    <p className="mt-0.5 truncate text-xs text-slate-500">{assignment.student_email || assignment.student.email}</p>
                  )}
                  <div className="mt-2"><Badge variant={assignment.status === 'submitted' || assignment.status === 'graded' ? 'success' : 'neutral'}>{assignment.status || 'assigned'}</Badge></div>
                  {notifications.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-slate-100 pt-2 dark:border-slate-800">
                      {notifications.map((notification) => (
                        <div key={notification.id} className="text-xs">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-slate-600 dark:text-slate-300">{notification.kind_display}</span>
                            <Badge variant={{ sent: 'success', failed: 'danger', pending: 'warning', queued: 'info', sending: 'info', skipped: 'neutral' }[notification.status] || 'neutral'}>
                              {notification.status_display || notification.status}
                            </Badge>
                          </div>
                          {notification.recipient_count > 1 && (
                            <p className="mt-1 text-slate-500">
                              One group email to {notification.recipient_count} students (one in To, others in CC).
                            </p>
                          )}
                          {notification.kind === 'reminder' && notification.status === 'pending' && notification.scheduled_for && (
                            <p className="mt-1 text-slate-500">Scheduled for {dateLabel(notification.scheduled_for)}</p>
                          )}
                          {notification.status === 'failed' && notification.last_error && (
                            <div className="mt-1 flex flex-wrap items-start justify-between gap-2">
                              <p className="min-w-0 flex-1 break-words text-rose-700 dark:text-rose-300">{notification.last_error}</p>
                              <Button size="sm" variant="ghost" loading={retryingNotificationId === notification.id} onClick={() => retryEmail(assignment.id, notification.id)}>
                                Retry email
                              </Button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {assignments.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center dark:border-slate-700">
                <p className="text-sm text-slate-500">No students assigned yet.</p>
                <Button className="mt-3" size="sm" variant="secondary" onClick={() => navigate(`/faculty/assessments/${id}/edit`)}>Assign students</Button>
              </div>
            )}
          </div>
          <div className="mt-5 border-t border-slate-100 pt-4 dark:border-slate-800">
            <p className="text-xs text-slate-500">Submission review and grading will be connected in Module 8.</p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AssessmentDetailsPage;
