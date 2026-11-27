import React, { useCallback, useEffect, useState } from 'react';
import { GraduationCap, LockKeyhole, RefreshCw, Search, ShieldAlert, UnlockKeyhole, Users } from 'lucide-react';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';

const getList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const formatLastLogin = (value) => {
  if (!value) return 'Never signed in';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const StudentAccessPage = () => {
  const pageSize = 50;
  const [students, setStudents] = useState([]);
  const [lockedAssignments, setLockedAssignments] = useState([]);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({
    count: 0,
    next: null,
    previous: null,
    summary: {},
  });
  const [search, setSearch] = useState('');
  const [lockFilter, setLockFilter] = useState('all');
  const [sortOrder, setSortOrder] = useState('name');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [pendingStudentId, setPendingStudentId] = useState(null);
  const [pendingCodingLockId, setPendingCodingLockId] = useState(null);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    try {
      const [studentsResult, lockedAssignmentsResult] = await Promise.allSettled([
        api.get(config.api.endpoints.users.studentsList, {
          params: {
            include_summary: 'true',
            page,
            page_size: pageSize,
            search,
            locked_only: lockFilter === 'locked' ? 'true' : undefined,
            sort: sortOrder,
          },
        }),
        api.get(config.api.endpoints.assessments.lockedAssignments, {
          params: { page_size: 100 },
        }),
      ]);
      if (studentsResult.status === 'rejected') throw studentsResult.reason;
      const data = studentsResult.value.data || {};
      setStudents(getList(data));
      setPagination({
        count: data.count ?? getList(data).length,
        next: data.next ?? null,
        previous: data.previous ?? null,
        summary: data.summary || {},
      });
      if (lockedAssignmentsResult.status === 'fulfilled') {
        setLockedAssignments(getList(lockedAssignmentsResult.value.data));
      } else {
        setLockedAssignments([]);
        addNotification('Locked assessment sessions could not be loaded.', 'warning');
      }
      setLoadError('');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to load students.';
      setLoadError(message);
      addNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addNotification, lockFilter, page, pageSize, search, sortOrder]);

  useEffect(() => {
    const timeout = window.setTimeout(loadStudents, search ? 250 : 0);
    return () => window.clearTimeout(timeout);
  }, [loadStudents]);

  const filteredStudents = students;
  const activeStudentCount = pagination.summary.active_students ?? pagination.count;
  const lockedCount = pagination.summary.login_locked_students ?? 0;
  const scoredStudentCount = pagination.summary.scored_students ?? 0;

  const clearLoginLock = async (student) => {
    const confirmed = window.confirm(
      `Clear recent failed login attempts for ${student.email}? This will let them try signing in again.`
    );
    if (!confirmed) return;

    setPendingStudentId(student.id);
    try {
      const response = await api.post(
        config.api.endpoints.users.clearLoginLock(student.id)
      );
      setStudents((current) => (
        lockFilter === 'locked'
          ? current.filter((item) => item.id !== student.id)
          : current.map((item) => (
            item.id === student.id ? { ...item, login_locked: false } : item
          ))
      ));
      if (lockFilter === 'locked' && student.login_locked) {
        setPagination((current) => ({
          ...current,
          count: Math.max(current.count - 1, 0),
        }));
      }
      if (student.login_locked) {
        setPagination((current) => ({
          ...current,
          summary: {
            ...current.summary,
            login_locked_students: Math.max(
              (current.summary.login_locked_students || 0) - 1,
              0,
            ),
          },
        }));
      }
      const clearedAttempts = response.data?.cleared_attempts ?? 0;
      const message = clearedAttempts
        ? `Cleared ${clearedAttempts} recent failed login attempt${clearedAttempts === 1 ? '' : 's'} for ${student.email}.`
        : `No recent failed login attempts needed clearing for ${student.email}.`;
      addNotification(message, 'success');
    } catch (error) {
      const message = error.response?.data?.detail || 'Could not clear the student login lock.';
      addNotification(message, 'error');
    } finally {
      setPendingStudentId(null);
    }
  };

  const removeCodingLock = async (assignment) => {
    setPendingCodingLockId(assignment.id);
    try {
      await api.post(config.api.endpoints.assessments.clearCheatingFlag(assignment.id));
      setLockedAssignments((current) => current.filter((item) => item.id !== assignment.id));
      addNotification('Coding lock removed and this assessment warning count reset to zero.', 'success');
    } catch (error) {
      const message = error.response?.data?.error
        || error.response?.data?.detail
        || error.response?.data?.message
        || `Could not remove the coding lock${error.response?.status ? ` (HTTP ${error.response.status})` : error.message ? `: ${error.message}` : '.'}`;
      addNotification(message, 'error');
    } finally {
      setPendingCodingLockId(null);
    }
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Students</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Review student progress and account access. Scores summarize assessments you created.
          </p>
        </div>
        <Button variant="secondary" icon={RefreshCw} loading={loading} onClick={loadStudents}>
          Refresh list
        </Button>
      </div>

      {loadError && !loading && (
        <Alert type="error" title="Students could not be loaded">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{loadError}</span>
            <Button variant="secondary" size="sm" onClick={loadStudents}>Try again</Button>
          </div>
        </Alert>
      )}

      <Card className="space-y-4 border-rose-200 dark:border-rose-900/50">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>Locked session students</CardTitle>
            <CardDescription>Students whose coding sessions are currently locked across assessments.</CardDescription>
          </div>
          <Badge variant={lockedAssignments.length ? 'danger' : 'neutral'}>{lockedAssignments.length} locked</Badge>
        </div>
        {loading ? (
          <p className="py-4 text-center text-sm text-slate-500">Loading locked sessions…</p>
        ) : lockedAssignments.length ? (
          <div className="space-y-2">
            {lockedAssignments.map((assignment) => (
              <div key={assignment.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 p-3 dark:border-rose-900/50 dark:bg-rose-950/20">
                <div className="min-w-0 text-sm">
                  <p className="font-semibold text-slate-900 dark:text-white">
                    <ShieldAlert size={15} className="mr-1 inline text-rose-500" />
                    {assignment.student_name || assignment.student_email || 'Student'}
                  </p>
                  <p className="truncate text-slate-600 dark:text-slate-300">{assignment.assessment_title || 'Assessment'}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {assignment.cheating_flag_reason === 'high_code_writing_speed'
                      ? `Code-writing speed: ${Math.round(assignment.cheating_flag_speed_wpm || 0)} WPM`
                      : ['rapid_code_insertion', 'bulk_code_insertion'].includes(assignment.cheating_flag_reason)
                        ? `Code insertion rate: ${(Number(assignment.cheating_flag_words_per_second) || 0).toFixed(1)} words/second`
                      : `Page-level event: ${String(assignment.cheating_flag_reason || 'integrity check').replaceAll('_', ' ')}`}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={UnlockKeyhole}
                  loading={pendingCodingLockId === assignment.id}
                  disabled={pendingCodingLockId !== null && pendingCodingLockId !== assignment.id}
                  onClick={() => removeCodingLock(assignment)}
                >
                  Remove coding lock
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            No locked coding sessions.
          </p>
        )}
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-primary-50 p-2 text-primary-700 dark:bg-primary-950/50 dark:text-primary-300"><Users size={18} /></span>
          <div><p className="text-xs text-slate-500">Active students</p><p className="text-xl font-bold text-slate-900 dark:text-white">{activeStudentCount}</p></div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-rose-50 p-2 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300"><LockKeyhole size={18} /></span>
          <div><p className="text-xs text-slate-500">Login locked</p><p className="text-xl font-bold text-slate-900 dark:text-white">{lockedCount}</p></div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"><GraduationCap size={18} /></span>
          <div><p className="text-xs text-slate-500">Students with graded results</p><p className="text-xl font-bold text-slate-900 dark:text-white">{scoredStudentCount}</p></div>
        </Card>
      </div>

      <Card>
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input
              aria-label="Search students"
              placeholder="Search name, email, roll number, or department…"
              value={search}
              className="pl-9"
              onChange={(event) => {
                setPage(1);
                setSearch(event.target.value);
              }}
            />
          </div>
          <Input as="select" aria-label="Filter students by login status" className="lg:max-w-48" value={lockFilter}
            onChange={(event) => {
              setPage(1);
              setLockFilter(event.target.value);
            }}>
            <option value="all">All students</option>
            <option value="locked">Login locked only</option>
          </Input>
          <Input as="select" aria-label="Sort students" className="lg:max-w-56" value={sortOrder}
            onChange={(event) => {
              setPage(1);
              setSortOrder(event.target.value);
            }}>
            <option value="name">Sort by name</option>
            <option value="score_high">Highest average score</option>
            <option value="score_low">Lowest average score</option>
          </Input>
        </div>

        <p className="mb-3 text-xs text-slate-500">
          Showing {filteredStudents.length} on this page, with {pagination.count} matching students. The average includes graded results and missed assessments as 0% after their deadline; upcoming and ungraded assessments are excluded.
        </p>

        {loading ? (
          <div className="py-16 text-center text-sm text-slate-500">Loading students…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead>
                <tr className="border-y border-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3 font-semibold">Student</th>
                  <th className="px-4 py-3 font-semibold">Profile</th>
                  <th className="px-4 py-3 font-semibold">Average score</th>
                  <th className="px-4 py-3 font-semibold">Assessment progress</th>
                  <th className="px-4 py-3 font-semibold">Last login</th>
                  <th className="px-4 py-3 font-semibold">Login status</th>
                  <th className="px-4 py-3 text-right font-semibold">Access</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="px-4 py-4 font-medium text-slate-900 dark:text-white">
                      {[student.first_name, student.last_name].filter(Boolean).join(' ') || 'Student'}
                      <a href={`mailto:${student.email}`} className="mt-1 block text-xs font-normal text-primary-700 hover:underline dark:text-primary-300">
                        {student.email}
                      </a>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      <p>{student.roll_number || 'No roll number'}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {[student.department, student.year_of_study ? `Year ${student.year_of_study}` : null].filter(Boolean).join(' · ') || 'Profile incomplete'}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      {student.average_score == null ? (
                        <span className="text-slate-500">No finalized outcomes</span>
                      ) : (
                        <>
                          <p className="font-semibold text-slate-900 dark:text-white">{Number(student.average_score).toFixed(1)}%</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {student.graded_assessment_count} graded{student.missed_assessment_count > 0 ? ` · ${student.missed_assessment_count} missed (0%)` : ''}
                          </p>
                        </>
                      )}
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      <p>{student.completed_assessment_count} submitted</p>
                      <p className="mt-1 text-xs text-slate-500">of {student.assigned_assessment_count} assigned</p>
                    </td>
                    <td className="px-4 py-4 text-xs text-slate-600 dark:text-slate-300">
                      {formatLastLogin(student.last_login)}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <Badge variant={student.login_locked ? 'danger' : 'neutral'}>
                        {student.login_locked ? 'Locked' : 'No lock'}
                      </Badge>
                    </td>
                    <td className="px-4 py-4 text-right">
                      {student.login_locked ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={UnlockKeyhole}
                          loading={pendingStudentId === student.id}
                          disabled={pendingStudentId !== null && pendingStudentId !== student.id}
                          onClick={() => clearLoginLock(student)}
                        >
                          Clear login lock
                        </Button>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredStudents.length === 0 && (
                  <tr>
                    <td colSpan="7" className="px-4 py-14 text-center">
                      <CardTitle className="text-base">
                        {pagination.count || search || lockFilter === 'locked'
                          ? 'No matching students'
                          : 'No students available'}
                      </CardTitle>
                      <CardDescription>
                        {pagination.count || search || lockFilter === 'locked'
                          ? 'Try another search, filter, or sort option.'
                          : 'Registered active students will appear here.'}
                      </CardDescription>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4 dark:border-slate-800">
          <span className="text-xs text-slate-500">
            Page {page} of {Math.max(1, Math.ceil(pagination.count / pageSize))}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!pagination.previous || loading}
              onClick={() => setPage((current) => Math.max(current - 1, 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!pagination.next || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default StudentAccessPage;
