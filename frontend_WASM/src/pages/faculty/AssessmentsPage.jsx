import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarClock, ClipboardList, Plus, Search, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const endpoints = config.api.endpoints;

const getList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const dateLabel = (value) => {
  if (!value) return 'Not scheduled';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not scheduled' : date.toLocaleString();
};

const statusVariant = (status) => ({
  active: 'success',
  scheduled: 'info',
  draft: 'neutral',
  closed: 'warning',
  archived: 'neutral',
}[status] || 'neutral');

const AssessmentsPage = () => {
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);

  const fetchAssessments = useCallback(async () => {
    try {
      const response = await api.get(endpoints.assessments.list, { params: { page_size: 100 } });
      setAssessments(getList(response.data));
      setLoadError('');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to load assessments.';
      setLoadError(message);
      addNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addNotification]);

  useEffect(() => {
    let active = true;
    api.get(endpoints.assessments.list, { params: { page_size: 100 } })
      .then((response) => {
        if (!active) return;
        setAssessments(getList(response.data));
        setLoadError('');
      })
      .catch((error) => {
        if (!active) return;
        const message = error.response?.data?.detail || 'Failed to load assessments.';
        setLoadError(message);
        addNotification(message, 'error');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [addNotification]);

  const retryFetchAssessments = () => {
    setLoading(true);
    fetchAssessments();
  };

  const filteredAssessments = useMemo(() => assessments.filter((assessment) => {
    const matchesSearch = assessment.title?.toLowerCase().includes(search.trim().toLowerCase());
    const matchesStatus = statusFilter === 'all' || assessment.status === statusFilter;
    return matchesSearch && matchesStatus;
  }), [assessments, search, statusFilter]);

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Assessments</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Create and manage scheduled assessments for your students.
          </p>
        </div>
        <Button onClick={() => navigate('/faculty/assessments/create')} icon={Plus}>
          Create assessment
        </Button>
      </div>

      <Card>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input aria-label="Search assessments" placeholder="Search by assessment title…" value={search}
              className="pl-9" onChange={(event) => setSearch(event.target.value)} />
          </div>
          <Input as="select" aria-label="Filter by status" className="sm:max-w-52" value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
            <option value="active">Active</option>
            <option value="closed">Closed</option>
            <option value="archived">Archived</option>
          </Input>
        </div>

        {loadError && !loading && (
          <Alert type="error" title="Assessments could not be loaded" className="mb-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>{loadError}</span>
              <Button variant="secondary" size="sm" onClick={retryFetchAssessments}>Try again</Button>
            </div>
          </Alert>
        )}

        {loading ? (
          <div className="py-20 text-center text-sm text-slate-500">Loading assessments…</div>
        ) : (
          <div className="min-w-0 max-w-full overflow-x-auto overscroll-x-contain">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead>
                <tr className="border-y border-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3 font-semibold">Assessment</th>
                  <th className="px-4 py-3 font-semibold">Questions</th>
                  <th className="px-4 py-3 font-semibold">Total marks</th>
                  <th className="px-4 py-3 font-semibold">Students</th>
                  <th className="px-4 py-3 font-semibold">Schedule</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssessments.map((assessment) => (
                  <tr key={assessment.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/70 dark:border-slate-800 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-4">
                      <p className="font-semibold text-slate-900 dark:text-white">{assessment.title}</p>
                      {assessment.description && (
                        <p className="mt-1 max-w-xs truncate text-xs text-slate-500">{assessment.description}</p>
                      )}
                    </td>
                    <td className="px-4 py-4 text-slate-700 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1.5"><ClipboardList size={15} />{assessment.question_count ?? assessment.assessment_questions?.length ?? 0}</span>
                    </td>
                    <td className="px-4 py-4 text-slate-700 dark:text-slate-300">{assessment.total_marks ?? 0}</td>
                    <td className="px-4 py-4 text-slate-700 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1.5"><Users size={15} />{assessment.assignment_count ?? 0}</span>
                    </td>
                    <td className="px-4 py-4 text-xs text-slate-600 dark:text-slate-400">
                      <span className="inline-flex items-start gap-1.5"><CalendarClock size={14} className="mt-0.5 shrink-0" />
                        <span>{dateLabel(assessment.start_time)}<br />to {dateLabel(assessment.end_time)}</span>
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <Badge variant={statusVariant(assessment.status)}>{assessment.status || 'draft'}</Badge>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="sm" onClick={() => navigate(`/faculty/assessments/${assessment.id}`)}>View</Button>
                        <Button variant="outline" size="sm" onClick={() => navigate(`/faculty/assessments/${assessment.id}/edit`)}>Edit</Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAssessments.length === 0 && (
                  <tr>
                    <td colSpan="7" className="px-4 py-14 text-center">
                      <CardTitle className="text-base">{assessments.length ? 'No matching assessments' : 'No assessments yet'}</CardTitle>
                      <CardDescription>
                        {assessments.length ? 'Try a different title or status filter.' : 'Create an assessment to schedule questions and assign students.'}
                      </CardDescription>
                      {!assessments.length && <Button className="mt-4" size="sm" onClick={() => navigate('/faculty/assessments/create')}>Create assessment</Button>}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default AssessmentsPage;
