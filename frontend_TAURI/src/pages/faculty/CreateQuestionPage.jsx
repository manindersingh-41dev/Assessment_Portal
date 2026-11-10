import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, LoaderCircle, Plus, Save, Trash2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../../api/client.js';
import { config } from '../../constants/config.js';
import { Alert, Badge, Card, CardDescription, CardTitle } from '../../components/Common.jsx';
import Button from '../../components/Button.jsx';
import Input from '../../components/Input.jsx';
import { useNotificationStore } from '../../store/notificationStore.js';

const initialQuestion = {
  title: '',
  description: '',
  input_format: '',
  output_format: '',
  constraints: '',
  sample_input: '',
  sample_output: '',
  sample_explanation: '',
  difficulty: 'easy',
  topic: '',
  language: 'c',
  total_marks: 10,
  status: 'draft',
  time_limit_seconds: 30,
  memory_limit_mb: 128,
};

const makeTestCase = (order, marks = 1) => ({
  input: '',
  expected_output: '',
  marks,
  is_sample: order === 1,
  order,
});

const apiErrorMessage = (error) => {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.error === 'string') return data.error;
  if (data && typeof data === 'object') {
    const getMessage = (value) => {
      if (typeof value === 'string') return value;
      if (Array.isArray(value)) return value.map(getMessage).find(Boolean);
      if (value && typeof value === 'object') return Object.values(value).map(getMessage).find(Boolean);
      return '';
    };
    const message = getMessage(data);
    if (message) return message;
  }
  return 'Could not save the question. Please try again.';
};

const CreateQuestionPage = () => {
  const { id } = useParams();
  const isEditing = Boolean(id);
  const navigate = useNavigate();
  const addNotification = useNotificationStore((state) => state.addNotification);
  const [question, setQuestion] = useState(initialQuestion);
  const [testCases, setTestCases] = useState([makeTestCase(1, 10)]);
  const [loading, setLoading] = useState(isEditing);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState('');
  const [testCaseError, setTestCaseError] = useState('');

  useEffect(() => {
    if (!isEditing) return undefined;

    let isCurrent = true;
    api.get(config.api.endpoints.questions.detail(id))
      .then(({ data }) => {
        if (!isCurrent) return;
        setQuestion({
          ...initialQuestion,
          title: data.title || '',
          description: data.description || '',
          input_format: data.input_format || '',
          output_format: data.output_format || '',
          constraints: data.constraints || '',
          sample_input: data.sample_input || '',
          sample_output: data.sample_output || '',
          sample_explanation: data.sample_explanation || '',
          difficulty: data.difficulty || 'medium',
          topic: data.topic || '',
          language: data.language || 'c',
          total_marks: data.total_marks ?? 10,
          status: data.status || 'draft',
          time_limit_seconds: data.time_limit_seconds ?? 30,
          memory_limit_mb: data.memory_limit_mb ?? 128,
        });
        const existingCases = Array.isArray(data.test_cases) ? data.test_cases : [];
        setTestCases(existingCases.length ? existingCases.map((testCase, index) => ({
          id: testCase.id,
          input: testCase.input || '',
          expected_output: testCase.expected_output || '',
          marks: testCase.marks ?? 1,
          is_sample: Boolean(testCase.is_sample),
          order: testCase.order || index + 1,
          has_results: Boolean(testCase.has_results),
        })) : [makeTestCase(1, data.total_marks ?? 10)]);
      })
      .catch((error) => {
        if (!isCurrent) return;
        const message = apiErrorMessage(error);
        setPageError(message);
        addNotification(message, 'error');
      })
      .finally(() => {
        if (isCurrent) setLoading(false);
      });

    return () => { isCurrent = false; };
  }, [id, isEditing, addNotification]);

  const testCaseMarks = useMemo(
    () => testCases.reduce((total, testCase) => total + (Number(testCase.marks) || 0), 0),
    [testCases]
  );

  const updateQuestion = (event) => {
    const { name, value } = event.target;
    setQuestion((current) => ({ ...current, [name]: value }));
  };

  const updateTestCase = (index, field, value) => {
    setTestCases((current) => current.map((testCase, currentIndex) => (
      currentIndex === index ? { ...testCase, [field]: value } : testCase
    )));
    setTestCaseError('');
  };

  const addTestCase = () => {
    setTestCases((current) => {
      const nextOrder = current.reduce((maximum, testCase) => Math.max(maximum, Number(testCase.order) || 0), 0) + 1;
      return [...current, makeTestCase(nextOrder)];
    });
    setTestCaseError('');
  };

  const removeTestCase = (index) => {
    setTestCases((current) => current
      .filter((_, currentIndex) => currentIndex !== index));
    setTestCaseError('');
  };

  const validateTestCases = () => {
    if (!testCases.length) return 'Add at least one test case.';
    if (!testCases.some((testCase) => testCase.is_sample)) return 'Mark at least one test case as a sample.';
    if (testCases.some((testCase) => !testCase.input.trim() || !testCase.expected_output.trim())) {
      return 'Every test case needs input and expected output.';
    }
    if (testCaseMarks !== Number(question.total_marks)) {
      return `Test-case marks total ${testCaseMarks}; it must equal the question total of ${question.total_marks}.`;
    }
    return '';
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setPageError('');
    const casesError = validateTestCases();
    setTestCaseError(casesError);
    if (casesError) return;

    setSaving(true);
    try {
      const payload = {
        ...question,
        total_marks: Number(question.total_marks),
        time_limit_seconds: Number(question.time_limit_seconds),
        memory_limit_mb: Number(question.memory_limit_mb),
        test_cases: testCases.map((testCase, index) => {
          const serializedCase = {
            ...testCase,
            marks: Number(testCase.marks),
            order: Number(testCase.order) || index + 1,
          };
          delete serializedCase.has_results;
          if (!isEditing || !serializedCase.id) delete serializedCase.id;
          return serializedCase;
        }),
      };

      if (isEditing) {
        await api.put(config.api.endpoints.questions.update(id), payload);
        addNotification('Question and test cases updated successfully.', 'success');
      } else {
        await api.post(config.api.endpoints.questions.create, payload);
        addNotification('Question and test cases created successfully.', 'success');
      }
      navigate('/faculty/questions');
    } catch (error) {
      const message = apiErrorMessage(error);
      setPageError(message);
      addNotification(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-72 items-center justify-center gap-3 text-sm text-slate-500" role="status">
        <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" /> Loading question…
      </div>
    );
  }

  if (pageError && isEditing && !question.title) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-8">
        <Alert type="error" title="Question unavailable">{pageError}</Alert>
        <Button variant="secondary" onClick={() => navigate('/faculty/questions')} icon={ArrowLeft}>Back to question bank</Button>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-4 sm:p-6 lg:p-8">
      <button
        type="button"
        onClick={() => navigate('/faculty/questions')}
        className="inline-flex items-center gap-2 rounded-lg text-sm font-medium text-slate-600 transition hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-slate-300 dark:hover:text-primary-300"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to question bank
      </button>

      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-primary-600 dark:text-primary-400">Faculty workspace</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">{isEditing ? 'Edit question' : 'Create question'}</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Add a programming problem, examples, and scoring details.</p>
      </div>

      {pageError && <Alert type="error" title="Could not save question">{pageError}</Alert>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <div className="mb-5">
            <CardTitle>Question details</CardTitle>
            <CardDescription>Describe the problem and the input/output contract.</CardDescription>
          </div>
          <div className="space-y-4">
            <Input label="Question title" name="title" value={question.title} onChange={updateQuestion} maxLength={200} required placeholder="e.g. Sum of an Array" />
            <Input as="textarea" label="Problem statement" name="description" value={question.description} onChange={updateQuestion} required rows={6} placeholder="Describe the problem clearly for students." />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input as="textarea" label="Input format" name="input_format" value={question.input_format} onChange={updateQuestion} required rows={3} />
              <Input as="textarea" label="Output format" name="output_format" value={question.output_format} onChange={updateQuestion} required rows={3} />
            </div>
            <Input as="textarea" label="Constraints" name="constraints" value={question.constraints} onChange={updateQuestion} required rows={3} placeholder="e.g. 1 ≤ N ≤ 10⁵" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input as="textarea" label="Sample input" name="sample_input" value={question.sample_input} onChange={updateQuestion} required rows={4} />
              <Input as="textarea" label="Sample output" name="sample_output" value={question.sample_output} onChange={updateQuestion} required rows={4} />
            </div>
            <Input as="textarea" label="Sample explanation (optional)" name="sample_explanation" value={question.sample_explanation} onChange={updateQuestion} rows={3} />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input as="select" label="Difficulty" name="difficulty" value={question.difficulty} onChange={updateQuestion}>
                <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
              </Input>
              <Input label="Topic (optional)" name="topic" value={question.topic || ''} onChange={updateQuestion} maxLength={100} placeholder="e.g. Arrays" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input as="select" label="Status" name="status" value={question.status} onChange={updateQuestion}>
                <option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option>
              </Input>
              <Input label="Language" value="C" readOnly helperText="The backend currently supports C questions." />
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <Input label="Total marks" name="total_marks" type="number" min="1" max="100" value={question.total_marks} onChange={updateQuestion} required />
              <Input label="Time limit (seconds)" name="time_limit_seconds" type="number" min="1" max="3600" value={question.time_limit_seconds} onChange={updateQuestion} required />
              <Input label="Memory limit (MB)" name="memory_limit_mb" type="number" min="1" max="2048" value={question.memory_limit_mb} onChange={updateQuestion} required />
            </div>
          </div>
        </Card>

        <Card>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div><CardTitle>Test-case builder</CardTitle><CardDescription>At least one sample is required. Test-case marks must add up to the question total.</CardDescription></div>
            <Button type="button" size="sm" variant="secondary" onClick={addTestCase} icon={Plus}>Add test case</Button>
          </div>
          {testCaseError && <Alert type="error" title="Check test cases" className="mb-4">{testCaseError}</Alert>}
          <div className="space-y-4">
            {testCases.map((testCase, index) => (
              <div key={testCase.id || `new-${index}`} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Test case {index + 1}</h3>
                    <Badge variant={testCase.is_sample ? 'info' : 'neutral'}>{testCase.is_sample ? 'Sample' : 'Hidden'}</Badge>
                    {testCase.has_results && <Badge variant="warning">Used in submissions</Badge>}
                  </div>
                  <Button type="button" size="sm" variant="ghost" disabled={testCase.has_results} title={testCase.has_results ? 'This test case has recorded results and cannot be removed' : 'Remove test case'} onClick={() => removeTestCase(index)} icon={Trash2}>Remove</Button>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <Input as="textarea" label="Input" rows={4} value={testCase.input} onChange={(event) => updateTestCase(index, 'input', event.target.value)} placeholder="Input passed to the program" required readOnly={testCase.has_results} />
                  <Input as="textarea" label="Expected output" rows={4} value={testCase.expected_output} onChange={(event) => updateTestCase(index, 'expected_output', event.target.value)} placeholder="Expected program output" required readOnly={testCase.has_results} />
                </div>
                <div className="mt-4 grid items-end gap-4 sm:grid-cols-[12rem_1fr]">
                  <Input label="Marks" type="number" min="1" max="100" value={testCase.marks} onChange={(event) => updateTestCase(index, 'marks', Number(event.target.value))} required readOnly={testCase.has_results} />
                  <label className="flex min-h-10 items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                    <input type="checkbox" checked={testCase.is_sample} disabled={testCase.has_results} onChange={(event) => updateTestCase(index, 'is_sample', event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 dark:border-slate-600 dark:bg-slate-900" />
                    Show this as a sample case
                  </label>
                </div>
              </div>
            ))}
          </div>
          <p className={`mt-4 text-right text-sm ${testCaseMarks === Number(question.total_marks) ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
            Test-case marks: {testCaseMarks} / {Number(question.total_marks) || 0}
          </p>
        </Card>

        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" onClick={() => navigate('/faculty/questions')}>Cancel</Button>
          <Button type="submit" loading={saving} disabled={loading} icon={Save}>{isEditing ? 'Save changes' : 'Save question'}</Button>
        </div>
      </form>
    </div>
  );
};

export default CreateQuestionPage;
