import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, ChevronLeft, ChevronRight, Plus, Search, Trash2, Upload, Users } from 'lucide-react';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';
import QuestionCreateModal from './QuestionCreateModal';
import BulkQuestionImportModal from './BulkQuestionImportModal';

const STEPS = ['Basic details', 'Questions', 'Settings', 'Student access', 'Review & publish'];
const endpoints = config.api.endpoints;

const asList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
};

const unwrapAssessment = (data) => data?.assessment || data;

const toDateTimeInput = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 16);
};

const formatDate = (value) => {
  if (!value) return 'Not set';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not set' : date.toLocaleString();
};

const getErrorMessage = (error, fallback) => {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.error === 'string') return data.error;
  if (data && typeof data === 'object') {
    const firstError = Object.values(data).flat(Infinity).find((item) => typeof item === 'string');
    if (firstError) return firstError;
  }
  return error?.message || fallback;
};

const getAssessmentQuestions = (assessment) => {
  const links = assessment?.questions || assessment?.assessment_questions || [];
  return links.map((link) => {
    const question = link.question && typeof link.question === 'object' ? link.question : null;
    return {
      id: question?.id || link.question || link.id,
      title: link.question_title || question?.title || link.title || 'Untitled question',
      difficulty: link.question_difficulty || question?.difficulty || link.difficulty || 'medium',
      marks: Number(link.marks || link.total_marks || question?.total_marks || 10),
    };
  }).filter((question) => question.id);
};

const CreateAssessmentWizard = ({ isEdit = false, assessmentId = null }) => {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(Boolean(isEdit));
  const [timerPreferenceLoaded, setTimerPreferenceLoaded] = useState(Boolean(isEdit));
  const [questionBank, setQuestionBank] = useState([]);
  const [questionSearch, setQuestionSearch] = useState('');
  const [questionDifficulty, setQuestionDifficulty] = useState('all');
  const [createQuestionOpen, setCreateQuestionOpen] = useState(false);
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const [students, setStudents] = useState([]);
  const [studentSearch, setStudentSearch] = useState('');
  const [studentsUnavailable, setStudentsUnavailable] = useState(false);
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [assessment, setAssessment] = useState(null);
  const [persistedAssessmentId, setPersistedAssessmentId] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    instructions: '',
    duration_minutes: 60,
    is_timed: true,
    is_open_to_all_students: true,
    start_time: '',
    end_time: '',
    selected_questions: [],
  });
  const timerPreferenceSaveQueueRef = useRef(Promise.resolve());

  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);
  const canEditStudents = !isEdit || (!assessment?.is_published && !assessment?.published_at);
  const totalMarks = useMemo(
    () => formData.selected_questions.reduce((sum, question) => sum + Number(question.marks || 0), 0),
    [formData.selected_questions],
  );
  const filteredQuestions = useMemo(() => questionBank.filter((question) => {
    const query = questionSearch.trim().toLowerCase();
    const matchesSearch = !query || question.title?.toLowerCase().includes(query);
    const matchesDifficulty = questionDifficulty === 'all'
      || question.difficulty?.toLowerCase() === questionDifficulty;
    return matchesSearch && matchesDifficulty;
  }), [questionBank, questionSearch, questionDifficulty]);
  const filteredStudents = useMemo(() => students.filter((student) => {
    const query = studentSearch.trim().toLowerCase();
    const name = `${student.first_name || ''} ${student.last_name || ''}`.trim().toLowerCase();
    return !query || name.includes(query) || student.email?.toLowerCase().includes(query);
  }), [students, studentSearch]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      const preferenceRequest = isEdit
        ? Promise.resolve(null)
        : api.get(endpoints.auth.facultyProfile);
      const [questionsResult, studentsResult, preferenceResult] = await Promise.allSettled([
        api.get(endpoints.questions.list),
        api.get(endpoints.users.studentsList),
        preferenceRequest,
      ]);

      if (!active) return;
      if (questionsResult.status === 'fulfilled') {
        setQuestionBank(asList(questionsResult.value.data));
      } else {
        addNotification('Could not load your question bank.', 'error');
      }
      if (studentsResult.status === 'fulfilled') {
        setStudents(asList(studentsResult.value.data));
      } else {
        setStudentsUnavailable(true);
      }
      if (!isEdit) {
        if (preferenceResult.status === 'fulfilled') {
          const savedTimerPreference = preferenceResult.value?.data?.default_assessment_is_timed;
          if (typeof savedTimerPreference === 'boolean') {
            setFormData((current) => ({ ...current, is_timed: savedTimerPreference }));
          }
        } else {
          addNotification('Could not load your saved timer preference; using the timed default.', 'warning');
        }
        setTimerPreferenceLoaded(true);
      }

      if (isEdit && assessmentId) {
        try {
          const response = await api.get(endpoints.assessments.detail(assessmentId));
          const current = unwrapAssessment(response.data);
          if (!active) return;
          setAssessment(current);
          setPersistedAssessmentId(current.id || assessmentId);
          setFormData({
            title: current.title || '',
            description: current.description || '',
            instructions: current.instructions || '',
            duration_minutes: current.duration_minutes || 60,
            is_timed: current.is_timed !== false,
            is_open_to_all_students: current.is_open_to_all_students !== false,
            start_time: toDateTimeInput(current.start_time || current.start_datetime),
            end_time: toDateTimeInput(current.end_time || current.end_datetime),
            selected_questions: getAssessmentQuestions(current),
          });

          try {
            const assignmentResponse = await api.get(endpoints.assessments.assignments(assessmentId));
            const assignmentData = assignmentResponse.data?.assignments || assignmentResponse.data;
            const ids = asList(assignmentData)
              .map((assignment) => assignment.student?.id || assignment.student)
              .filter(Boolean);
            if (active) setSelectedStudents(ids);
          } catch {
            // Assignment data is optional for editing assessment content.
          }
        } catch (error) {
          if (active) addNotification(getErrorMessage(error, 'Failed to load this assessment.'), 'error');
        }
      }

      if (active) setInitialLoading(false);
    };

    load();
    return () => { active = false; };
  }, [addNotification, assessmentId, isEdit]);

  const updateField = (field, value) => {
    setFormData((current) => ({ ...current, [field]: value }));
  };

  const updateTimerPreference = (value) => {
    updateField('is_timed', value);
    timerPreferenceSaveQueueRef.current = timerPreferenceSaveQueueRef.current
      .catch(() => undefined)
      .then(() => api.patch(endpoints.auth.facultyProfile, {
        default_assessment_is_timed: value,
      }))
      .catch((error) => {
        addNotification(
          getErrorMessage(error, 'This assessment setting changed, but your default preference could not be saved.'),
          'warning',
        );
      });
  };

  const addQuestion = (question) => {
    if (formData.selected_questions.some((item) => item.id === question.id)) return;
    setFormData((current) => ({
      ...current,
      selected_questions: [
        ...current.selected_questions,
        { ...question, marks: Number(question.total_marks || question.marks || 10) },
      ],
    }));
  };

  const handleQuestionCreated = (question) => {
    setQuestionBank((current) => [question, ...current.filter((item) => item.id !== question.id)]);
    addQuestion(question);
    setQuestionSearch('');
    setQuestionDifficulty('all');
    addNotification('Question created and added to this assessment.', 'success');
  };

  const handleBulkQuestionsImported = (createdQuestions) => {
    setQuestionBank((current) => [
      ...createdQuestions,
      ...current.filter((question) => !createdQuestions.some((created) => created.id === question.id)),
    ]);
    setFormData((current) => {
      const selectedIds = new Set(current.selected_questions.map((question) => question.id));
      const additions = createdQuestions
        .filter((question) => !selectedIds.has(question.id))
        .map((question) => ({
          ...question,
          marks: Number(question.total_marks || 10),
        }));
      return {
        ...current,
        selected_questions: [...current.selected_questions, ...additions],
      };
    });
    setQuestionSearch('');
    setQuestionDifficulty('all');
    addNotification(
      `${createdQuestions.length} questions and their test cases were added to the question bank and this assessment.`,
      'success',
    );
  };

  const removeQuestion = (questionId) => {
    setFormData((current) => ({
      ...current,
      selected_questions: current.selected_questions.filter((question) => question.id !== questionId),
    }));
  };

  const updateQuestionMarks = (questionId, marks) => {
    setFormData((current) => ({
      ...current,
      selected_questions: current.selected_questions.map((question) => (
        question.id === questionId ? { ...question, marks: Number(marks) } : question
      )),
    }));
  };

  const toggleStudent = (studentId) => {
    setSelectedStudents((current) => current.includes(studentId)
      ? current.filter((id) => id !== studentId)
      : [...current, studentId]);
  };

  const validateStep = () => {
    if (step === 0 && !formData.title.trim()) {
      addNotification('Enter an assessment title to continue.', 'warning');
      return false;
    }
    if (step === 1 && formData.selected_questions.length === 0) {
      addNotification('Add at least one question to continue.', 'warning');
      return false;
    }
    if (step === 2) {
      const start = new Date(formData.start_time);
      const end = new Date(formData.end_time);
      if (!formData.start_time || !formData.end_time || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        addNotification('Set a start and end time for the assessment.', 'warning');
        return false;
      }
      if (end <= start) {
        addNotification('The end time must be after the start time.', 'warning');
        return false;
      }
      if (formData.is_timed && (!Number.isInteger(Number(formData.duration_minutes)) || Number(formData.duration_minutes) < 1)) {
        addNotification('Assessment duration must be at least one minute.', 'warning');
        return false;
      }
      if (totalMarks > 1000) {
        addNotification('Assessment total marks cannot exceed 1,000.', 'warning');
        return false;
      }
    }
    if (step === 3 && canEditStudents
      && !formData.is_open_to_all_students && selectedStudents.length === 0) {
      addNotification('Select at least one student, or make the assessment available to all students.', 'warning');
      return false;
    }
    return true;
  };

  const nextStep = () => {
    if (validateStep()) setStep((current) => Math.min(current + 1, STEPS.length - 1));
  };

  const payload = () => ({
    title: formData.title.trim(),
    description: formData.description,
    instructions: formData.instructions,
    duration_minutes: Number(formData.duration_minutes),
    is_timed: formData.is_timed,
    is_open_to_all_students: formData.is_open_to_all_students,
    start_time: new Date(formData.start_time).toISOString(),
    end_time: new Date(formData.end_time).toISOString(),
    total_marks: totalMarks,
    questions: formData.selected_questions.map((question, index) => ({
      question: question.id,
      marks: Number(question.marks),
      order: index + 1,
    })),
  });

  const publishAndAssign = async (id) => {
    if (!assessment?.is_published) {
      await api.post(endpoints.assessments.publish(id));
      setAssessment((current) => ({ ...current, is_published: true, status: 'active' }));
    }
    if (!formData.is_open_to_all_students && selectedStudents.length > 0) {
      await api.post(endpoints.assessments.assign(id), { student_ids: selectedStudents });
    }
  };

  const handleSubmit = async () => {
    if (!validateStep() || formData.selected_questions.some((question) => question.marks < 1 || question.marks > 100)) {
      if (formData.selected_questions.some((question) => question.marks < 1 || question.marks > 100)) {
        addNotification('Question marks must be between 1 and 100.', 'warning');
      }
      return;
    }

    setLoading(true);
    let id = persistedAssessmentId;
    try {
      await timerPreferenceSaveQueueRef.current;
      if (isEdit && id) {
        const response = await api.put(endpoints.assessments.update(id), payload());
        const saved = unwrapAssessment(response.data);
        setAssessment((current) => ({ ...current, ...saved }));
      } else if (!id) {
        const response = await api.post(endpoints.assessments.create, payload());
        const saved = unwrapAssessment(response.data);
        id = saved.id;
        setPersistedAssessmentId(id);
        setAssessment(saved);
      }

      if (!id) throw new Error('The server did not return an assessment ID.');
      await publishAndAssign(id);
      addNotification(
        formData.is_open_to_all_students
          ? 'Assessment published for all current and future students.'
          : 'Assessment published and assigned to the selected students.',
        'success',
      );
      navigate('/faculty/assessments');
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to save the assessment.');
      addNotification(
        id ? `Assessment ${id === persistedAssessmentId ? 'was saved' : 'was created'}, but the next step failed: ${message}` : message,
        'error',
        7000,
      );
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return <div className="mx-auto max-w-5xl p-6 text-center text-slate-500">Loading assessment…</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {isEdit ? 'Edit assessment' : 'Create assessment'}
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Set the schedule, choose questions, and assign students.
        </p>
      </div>

      <Card className="p-3 sm:p-4">
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {STEPS.map((label, index) => (
            <li key={label}>
              <button
                type="button"
                onClick={() => index < step && setStep(index)}
                disabled={index > step}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold transition sm:text-sm ${
                  index === step
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-950/50 dark:text-primary-300'
                    : index < step
                      ? 'text-emerald-700 dark:text-emerald-300'
                      : 'text-slate-400'
                }`}
              >
                <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                  index < step ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-slate-100 dark:bg-slate-800'
                }`}>
                  {index < step ? <Check size={14} /> : index + 1}
                </span>
                <span>{label}</span>
              </button>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="p-5 sm:p-7">
        {step === 0 && (
          <div className="space-y-5">
            <div>
              <CardTitle>Basic details</CardTitle>
              <CardDescription>Give students a clear name and context for this assessment.</CardDescription>
            </div>
            <Input label="Assessment title" required value={formData.title} maxLength={200}
              onChange={(event) => updateField('title', event.target.value)} />
            <Input label="Description" as="textarea" rows={3} value={formData.description}
              onChange={(event) => updateField('description', event.target.value)} />
            <Input label="Instructions for students" as="textarea" rows={4} value={formData.instructions}
              onChange={(event) => updateField('instructions', event.target.value)} />
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <CardTitle>Choose questions</CardTitle>
                <CardDescription>Choose from your question bank or create a question here, then set its assessment marks.</CardDescription>
              </div>
              <Badge variant="info">{formData.selected_questions.length} selected · {totalMarks} marks</Badge>
            </div>
            <div className="grid gap-5 lg:grid-cols-2">
              <section className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-semibold text-slate-900 dark:text-white">Question bank</h3>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => setBulkImportOpen(true)} icon={Upload}>
                      Bulk upload
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => setCreateQuestionOpen(true)}>
                      <Plus size={15} />Add new question
                    </Button>
                  </div>
                </div>
                <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_180px]">
                  <Input aria-label="Search questions" placeholder="Search questions…" value={questionSearch}
                    onChange={(event) => setQuestionSearch(event.target.value)} />
                  <Input as="select" aria-label="Filter by difficulty" value={questionDifficulty}
                    onChange={(event) => setQuestionDifficulty(event.target.value)}>
                    <option value="all">All difficulties</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </Input>
                </div>
                <div className="max-h-96 space-y-2 overflow-y-auto">
                  {filteredQuestions.map((question) => {
                    const selected = formData.selected_questions.some((item) => item.id === question.id);
                    return (
                      <div key={question.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{question.title}</p>
                          <p className="mt-1 text-xs capitalize text-slate-500">
                            {question.difficulty || 'medium'} · {question.total_marks || question.marks || 10} marks
                          </p>
                        </div>
                        <Button size="sm" variant={selected ? 'secondary' : 'primary'} disabled={selected}
                          onClick={() => addQuestion(question)}>
                          {selected ? 'Added' : 'Add'}
                        </Button>
                      </div>
                    );
                  })}
                  {filteredQuestions.length === 0 && (
                    <p className="py-8 text-center text-sm text-slate-500">
                      {questionBank.length ? 'No questions match those filters.' : 'No questions found in your question bank.'}
                    </p>
                  )}
                </div>
              </section>

              <section>
                <h3 className="mb-3 font-semibold text-slate-900 dark:text-white">Selected questions</h3>
                <div className="max-h-[29rem] space-y-2 overflow-y-auto">
                  {formData.selected_questions.map((question, index) => (
                    <div key={question.id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                      <span className="text-xs font-semibold text-slate-400">{index + 1}.</span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{question.title}</p>
                        <p className="mt-1 text-xs capitalize text-slate-500">{question.difficulty}</p>
                      </div>
                      <label className="flex items-center gap-1 text-xs text-slate-500">
                        <span className="sr-only">Marks for {question.title}</span>
                        <input type="number" min="1" max="100" value={question.marks}
                          onChange={(event) => updateQuestionMarks(question.id, event.target.value)}
                          className="w-16 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-center text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                        marks
                      </label>
                      <Button size="sm" variant="ghost" aria-label={`Remove ${question.title}`} onClick={() => removeQuestion(question.id)}>
                        <Trash2 size={15} />
                      </Button>
                    </div>
                  ))}
                  {formData.selected_questions.length === 0 && (
                    <p className="rounded-lg border border-dashed border-slate-300 py-10 text-center text-sm text-slate-500 dark:border-slate-700">
                      Select questions from the bank to build this assessment.
                    </p>
                  )}
                </div>
              </section>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div>
              <CardTitle>Schedule and settings</CardTitle>
              <CardDescription>Set when students can start and whether their attempt has a time limit.</CardDescription>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Start date and time" type="datetime-local" required value={formData.start_time}
                onChange={(event) => updateField('start_time', event.target.value)} />
              <Input label="End date and time" type="datetime-local" required value={formData.end_time}
                onChange={(event) => updateField('end_time', event.target.value)} />
              <fieldset className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700 sm:col-span-2">
                <legend className="px-1 text-sm font-medium text-slate-700 dark:text-slate-200">Time limit</legend>
                <label className="flex cursor-pointer items-start gap-3">
                  <input type="checkbox" checked={formData.is_timed} disabled={!timerPreferenceLoaded}
                    onChange={(event) => updateTimerPreference(event.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
                  <span>
                    <span className="block text-sm font-medium text-slate-900 dark:text-white">Enforce a completion timer</span>
                    <span className="mt-1 block text-xs text-slate-500">When off, students must start during the scheduled window, then may leave and resume later without a time limit.</span>
                    <span className="mt-1 block text-xs text-slate-500">{timerPreferenceLoaded ? 'Your choice is saved as the default for future assessments.' : 'Loading your saved timer preference…'}</span>
                  </span>
                </label>
              </fieldset>
              <Input label="Duration (minutes)" type="number" min="1" max="480" required={formData.is_timed}
                disabled={!formData.is_timed} value={formData.duration_minutes}
                onChange={(event) => updateField('duration_minutes', event.target.value)} />
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Total marks</p>
                <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">{totalMarks}</p>
                <p className="mt-1 text-xs text-slate-500">Calculated from the selected question marks.</p>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <CardTitle>Who can access this assessment?</CardTitle>
                <CardDescription>By default, every registered student can see it, including students who register later.</CardDescription>
              </div>
              <Badge variant="info"><Users size={13} className="mr-1" />
                {formData.is_open_to_all_students ? 'All current and future students' : `${selectedStudents.length} selected`}
              </Badge>
            </div>
            <fieldset disabled={!canEditStudents} className="grid gap-3 md:grid-cols-2">
              <legend className="sr-only">Assessment audience</legend>
              <label className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition ${formData.is_open_to_all_students ? 'border-primary-500 bg-primary-50 dark:bg-primary-950/30' : 'border-slate-200 dark:border-slate-700'}`}>
                <input type="radio" name="assessment-audience" checked={formData.is_open_to_all_students}
                  onChange={() => updateField('is_open_to_all_students', true)} className="mt-1" />
                <span>
                  <span className="block text-sm font-semibold">All current and future students</span>
                  <span className="mt-1 block text-xs text-slate-500">Any student can see and start this assessment after it is published.</span>
                </span>
              </label>
              <label className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition ${!formData.is_open_to_all_students ? 'border-primary-500 bg-primary-50 dark:bg-primary-950/30' : 'border-slate-200 dark:border-slate-700'}`}>
                <input type="radio" name="assessment-audience" checked={!formData.is_open_to_all_students}
                  onChange={() => updateField('is_open_to_all_students', false)} className="mt-1" />
                <span>
                  <span className="block text-sm font-semibold">Selected students only</span>
                  <span className="mt-1 block text-xs text-slate-500">Choose registered students below. Later registrations will not be included.</span>
                </span>
              </label>
            </fieldset>
            {formData.is_open_to_all_students && (
              <Alert type="info">All students can find this assessment in their dashboard. New registrations will receive access automatically.</Alert>
            )}
            {!formData.is_open_to_all_students && studentsUnavailable && (
              <Alert type="warning" title="Student directory unavailable">
                The student list could not be loaded. Try again before publishing a student-specific assessment.
              </Alert>
            )}
            {!formData.is_open_to_all_students && isEdit && (assessment?.is_published || assessment?.published_at) && (
              <Alert type="info">
                Existing assignments remain in place. You can add students here; unchecking a student does not revoke an existing assignment.
              </Alert>
            )}
            {!canEditStudents && (
              <Alert type="info">Student assignments are managed through the assignment endpoint.</Alert>
            )}
            {!formData.is_open_to_all_students && (
              <>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <div className="relative flex-1">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <Input aria-label="Search students" placeholder="Search by name or email…" value={studentSearch}
                      className="pl-9" onChange={(event) => setStudentSearch(event.target.value)} />
                  </div>
                  <Button variant="secondary" onClick={() => setSelectedStudents(students.map((student) => student.id))}
                    disabled={students.length === 0}>Select all</Button>
                  <Button variant="ghost" onClick={() => setSelectedStudents([])} disabled={selectedStudents.length === 0}>Clear</Button>
                </div>
                <div className="max-h-80 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700">
                  {filteredStudents.map((student) => (
                    <label key={student.id} className="flex cursor-pointer items-center gap-3 border-b border-slate-100 p-3 last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/60">
                      <input type="checkbox" checked={selectedStudents.includes(student.id)} onChange={() => toggleStudent(student.id)}
                        className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-900 dark:text-white">
                          {[student.first_name, student.last_name].filter(Boolean).join(' ') || student.email}
                        </span>
                        <span className="block truncate text-xs text-slate-500">{student.email}</span>
                      </span>
                    </label>
                  ))}
                  {filteredStudents.length === 0 && (
                    <p className="p-8 text-center text-sm text-slate-500">
                      {students.length ? 'No students match that search.' : 'No students are available to assign.'}
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-5">
            <div>
              <CardTitle>Review and publish</CardTitle>
              <CardDescription>Confirm the assessment details before making it available.</CardDescription>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Title</p><p className="mt-1 font-semibold">{formData.title || 'Untitled'}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Questions</p><p className="mt-1 font-semibold">{formData.selected_questions.length}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Total marks</p><p className="mt-1 font-semibold">{totalMarks}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Time limit</p><p className="mt-1 font-semibold">{formData.is_timed ? `${formData.duration_minutes} minutes` : 'No time limit after starting'}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Starts</p><p className="mt-1 font-semibold">{formatDate(formData.start_time)}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
                <p className="text-xs text-slate-500">Ends</p><p className="mt-1 font-semibold">{formatDate(formData.end_time)}</p>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <p className="text-sm font-semibold">
                {formData.is_open_to_all_students ? 'Access: all current and future students' : `Students to assign: ${selectedStudents.length}`}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {formData.is_open_to_all_students
                  ? 'Every registered student can see this assessment after publication, including students who register later.'
                  : 'The assessment will be published only for the selected students.'}
              </p>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">Question order</h3>
              <ol className="space-y-2">
                {formData.selected_questions.map((question, index) => (
                  <li key={question.id} className="flex justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800">
                    <span>{index + 1}. {question.title}</span><span className="shrink-0 text-slate-500">{question.marks} marks</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}

        <div className="mt-8 flex flex-wrap justify-between gap-3 border-t border-slate-100 pt-5 dark:border-slate-800">
          <Button variant="secondary" onClick={() => step === 0 ? navigate('/faculty/assessments') : setStep((current) => current - 1)}>
            <ChevronLeft size={16} />{step === 0 ? 'Cancel' : 'Back'}
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={nextStep}>Continue<ChevronRight size={16} /></Button>
          ) : (
            <Button onClick={handleSubmit} loading={loading}>
              {isEdit && assessment?.is_published ? 'Save changes' : 'Publish assessment'}
            </Button>
          )}
        </div>
      </Card>

      <QuestionCreateModal
        isOpen={createQuestionOpen}
        onClose={() => setCreateQuestionOpen(false)}
        onCreated={handleQuestionCreated}
      />
      <BulkQuestionImportModal
        isOpen={bulkImportOpen}
        onClose={() => setBulkImportOpen(false)}
        onImported={handleBulkQuestionsImported}
      />
    </div>
  );
};

export default CreateAssessmentWizard;
