import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { GraduationCap, LockKeyhole, RefreshCw, Search, UnlockKeyhole, Users } from 'lucide-react';
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
  const [students, setStudents] = useState([]);
  const [search, setSearch] = useState('');
  const [lockFilter, setLockFilter] = useState('all');
  const [sortOrder, setSortOrder] = useState('name');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [pendingStudentId, setPendingStudentId] = useState(null);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(config.api.endpoints.users.studentsList, {
        params: { include_summary: 'true' },
      });
      setStudents(getList(response.data));
      setLoadError('');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to load students.';
      setLoadError(message);
      addNotification(message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addNotification]);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const filteredStudents = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = students.filter((student) => {
      const name = `${student.first_name || ''} ${student.last_name || ''}`.trim().toLowerCase();
      const searchable = [name, student.email, student.roll_number, student.department]
        .some((value) => String(value || '').toLowerCase().includes(query));
      const matchesLock = lockFilter !== 'locked' || student.login_locked;
      return searchable && matchesLock;
    });

    return filtered.sort((left, right) => {
      if (sortOrder === 'score_high') {
        if (left.average_score == null) return 1;
        if (right.average_score == null) return -1;
        return Number(right.average_score) - Number(left.average_score);
      }
      if (sortOrder === 'score_low') {
        if (left.average_score == null) return 1;
        if (right.average_score == null) return -1;
        return Number(left.average_score) - Number(right.average_score);
      }
      const leftName = `${left.first_name || ''} ${left.last_name || ''}`.trim();
      const rightName = `${right.first_name || ''} ${right.last_name || ''}`.trim();
      return leftName.localeCompare(rightName) || left.email.localeCompare(right.email);
    });
  }, [lockFilter, search, sortOrder, students]);

  const lockedCount = students.filter((student) => student.login_locked).length;
  const scoredStudentCount = students.filter((student) => student.average_score != null).length;

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
      setStudents((current) => current.map((item) => (
        item.id === student.id ? { ...item, login_locked: false } : item
      )));
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

      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-primary-50 p-2 text-primary-700 dark:bg-primary-950/50 dark:text-primary-300"><Users size={18} /></span>
          <div><p className="text-xs text-slate-500">Active students</p><p className="text-xl font-bold text-slate-900 dark:text-white">{students.length}</p></div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-rose-50 p-2 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300"><LockKeyhole size={18} /></span>
          <div><p className="text-xs text-slate-500">Login locked</p><p className="text-xl font-bold text-slate-900 dark:text-white">{lockedCount}</p></div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"><GraduationCap size={18} /></span>
          <div><p className="text-xs text-slate-500">Students with graded scores</p><p className="text-xl font-bold text-slate-900 dark:text-white">{scoredStudentCount}</p></div>
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
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <Input as="select" aria-label="Filter students by login status" className="lg:max-w-48" value={lockFilter}
            onChange={(event) => setLockFilter(event.target.value)}>
            <option value="all">All students</option>
            <option value="locked">Login locked only</option>
          </Input>
          <Input as="select" aria-label="Sort students" className="lg:max-w-56" value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}>
            <option value="name">Sort by name</option>
            <option value="score_high">Highest average score</option>
            <option value="score_low">Lowest average score</option>
          </Input>
        </div>

        <p className="mb-3 text-xs text-slate-500">
          Showing {filteredStudents.length} of {students.length}. Average scores use your graded assessments only.
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
                        <span className="text-slate-500">No graded scores</span>
                      ) : (
                        <>
                          <p className="font-semibold text-slate-900 dark:text-white">{Number(student.average_score).toFixed(1)}%</p>
                          <p className="mt-1 text-xs text-slate-500">{student.graded_assessment_count} graded</p>
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
                        {students.length ? 'No matching students' : 'No students available'}
                      </CardTitle>
                      <CardDescription>
                        {students.length ? 'Try another search, filter, or sort option.' : 'Registered active students will appear here.'}
                      </CardDescription>
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

export default StudentAccessPage;
