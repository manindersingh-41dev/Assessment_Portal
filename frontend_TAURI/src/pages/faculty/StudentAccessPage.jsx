import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, UnlockKeyhole, Users } from 'lucide-react';
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

const StudentAccessPage = () => {
  const [students, setStudents] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [pendingStudentId, setPendingStudentId] = useState(null);
  const addNotification = useNotificationStore((state) => state.addNotification);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(config.api.endpoints.users.studentsList);
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
    if (!query) return students;
    return students.filter((student) => {
      const name = `${student.first_name || ''} ${student.last_name || ''}`.trim().toLowerCase();
      return name.includes(query) || student.email?.toLowerCase().includes(query);
    });
  }, [search, students]);

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
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Student access</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Find a student and clear their login lock after verifying their identity.
        </p>
      </div>

      {loadError && !loading && (
        <Alert type="error" title="Students could not be loaded">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{loadError}</span>
            <Button variant="secondary" size="sm" onClick={loadStudents}>Try again</Button>
          </div>
        </Alert>
      )}

      <Card>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input
              aria-label="Search students"
              placeholder="Search by student name or email…"
              value={search}
              className="pl-9"
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <span className="inline-flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <Users size={16} aria-hidden="true" />
            {students.length} student{students.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm text-slate-500">Loading students…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead>
                <tr className="border-y border-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3 font-semibold">Student</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Login status</th>
                  <th className="px-4 py-3 text-right font-semibold">Access</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="px-4 py-4 font-medium text-slate-900 dark:text-white">
                      {[student.first_name, student.last_name].filter(Boolean).join(' ') || 'Student'}
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">{student.email}</td>
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
                    <td colSpan="4" className="px-4 py-14 text-center">
                      <CardTitle className="text-base">
                        {students.length ? 'No matching students' : 'No students available'}
                      </CardTitle>
                      <CardDescription>
                        {students.length ? 'Try another name or email.' : 'Registered active students will appear here.'}
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
