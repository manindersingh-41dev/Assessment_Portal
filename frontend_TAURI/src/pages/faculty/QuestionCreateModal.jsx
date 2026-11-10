import React, { useEffect, useMemo, useState } from 'react';
import { Plus, Save, Trash2 } from 'lucide-react';
import { Alert, Badge, CardDescription, CardTitle } from '../../components/Common';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Modal } from '../../components/Modal';
import api from '../../api/client';
import { config } from '../../constants/config';

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
  total_marks: 10,
  time_limit_seconds: 30,
  memory_limit_mb: 128,
};

const makeTestCase = (order, marks = 10) => ({
  input: '',
  expected_output: '',
  marks,
  is_sample: order === 1,
  order,
});

const getErrorMessage = (error) => {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.error === 'string') return data.error;
  if (data && typeof data === 'object') {
    const findMessage = (value) => {
      if (typeof value === 'string') return value;
      if (Array.isArray(value)) return value.map(findMessage).find(Boolean);
      if (value && typeof value === 'object') return Object.values(value).map(findMessage).find(Boolean);
      return '';
    };
    const message = findMessage(data);
    if (message) return message;
  }
  return 'Could not create this question. Please try again.';
};

const QuestionCreateModal = ({ isOpen, onClose, onCreated }) => {
  const [question, setQuestion] = useState(initialQuestion);
  const [testCases, setTestCases] = useState([makeTestCase(1, 10)]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [testCaseError, setTestCaseError] = useState('');
  const testCaseMarks = useMemo(
    () => testCases.reduce((total, testCase) => total + (Number(testCase.marks) || 0), 0),
    [testCases],
  );

  useEffect(() => {
    if (!isOpen) return;
    setQuestion(initialQuestion);
    setTestCases([makeTestCase(1, 10)]);
    setError('');
    setTestCaseError('');
  }, [isOpen]);

  const close = () => {
    if (!saving) onClose();
  };

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
    setTestCases((current) => [
      ...current,
      makeTestCase(current.reduce((maximum, testCase) => Math.max(maximum, Number(testCase.order) || 0), 0) + 1, 1),
    ]);
  };

  const removeTestCase = (index) => {
    setTestCases((current) => current.filter((_, currentIndex) => currentIndex !== index));
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
    setError('');
    const validationError = validateTestCases();
    setTestCaseError(validationError);
    if (validationError) return;

    setSaving(true);
    try {
      const response = await api.post(config.api.endpoints.questions.create, {
        ...question,
        total_marks: Number(question.total_marks),
        time_limit_seconds: Number(question.time_limit_seconds),
        memory_limit_mb: Number(question.memory_limit_mb),
        test_cases: testCases.map((testCase, index) => ({
          ...testCase,
          marks: Number(testCase.marks),
          order: index + 1,
        })),
      });
      const createdQuestion = response.data?.question || response.data;
      if (!createdQuestion?.id) throw new Error('The server did not return the new question.');
      onCreated(createdQuestion);
      onClose();
    } catch (createError) {
      setError(getErrorMessage(createError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Add a question to the bank" size="2xl">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <CardTitle>Create question</CardTitle>
          <CardDescription>The question will be saved to your bank and added to this assessment.</CardDescription>
        </div>

        {error && <Alert type="error" title="Question was not created">{error}</Alert>}
        {testCaseError && <Alert type="error" title="Check the test cases">{testCaseError}</Alert>}

        <div className="space-y-4">
          <Input label="Question title" name="title" value={question.title} onChange={updateQuestion} maxLength={200} required />
          <Input as="textarea" label="Problem statement" name="description" value={question.description} onChange={updateQuestion} rows={4} required />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input as="textarea" label="Input format" name="input_format" value={question.input_format} onChange={updateQuestion} rows={3} required />
            <Input as="textarea" label="Output format" name="output_format" value={question.output_format} onChange={updateQuestion} rows={3} required />
          </div>
          <Input as="textarea" label="Constraints" name="constraints" value={question.constraints} onChange={updateQuestion} rows={3} required />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input as="textarea" label="Sample input" name="sample_input" value={question.sample_input} onChange={updateQuestion} rows={3} required />
            <Input as="textarea" label="Sample output" name="sample_output" value={question.sample_output} onChange={updateQuestion} rows={3} required />
          </div>
          <Input as="textarea" label="Sample explanation (optional)" name="sample_explanation" value={question.sample_explanation} onChange={updateQuestion} rows={2} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input as="select" label="Difficulty" name="difficulty" value={question.difficulty} onChange={updateQuestion}>
              <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
            </Input>
            <Input label="Topic (optional)" name="topic" value={question.topic} onChange={updateQuestion} maxLength={100} />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input label="Total marks" name="total_marks" type="number" min="1" max="100" value={question.total_marks} onChange={updateQuestion} required />
            <Input label="Time limit (seconds)" name="time_limit_seconds" type="number" min="1" max="3600" value={question.time_limit_seconds} onChange={updateQuestion} required />
            <Input label="Memory limit (MB)" name="memory_limit_mb" type="number" min="1" max="2048" value={question.memory_limit_mb} onChange={updateQuestion} required />
          </div>
        </div>

        <section className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h3 className="font-semibold text-slate-900 dark:text-white">Test cases</h3><p className="text-xs text-slate-500">At least one sample is required; marks must add up to the question total.</p></div>
            <Button type="button" size="sm" variant="secondary" onClick={addTestCase}><Plus size={15} />Add case</Button>
          </div>
          {testCases.map((testCase, index) => (
            <div key={index} className="space-y-3 rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><span className="text-sm font-medium">Case {index + 1}</span><Badge variant={testCase.is_sample ? 'info' : 'neutral'}>{testCase.is_sample ? 'Sample' : 'Hidden'}</Badge></div>
                <Button type="button" size="sm" variant="ghost" disabled={testCases.length === 1} onClick={() => removeTestCase(index)} aria-label={`Remove test case ${index + 1}`}><Trash2 size={15} /></Button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input as="textarea" label="Input" rows={2} value={testCase.input} onChange={(event) => updateTestCase(index, 'input', event.target.value)} required />
                <Input as="textarea" label="Expected output" rows={2} value={testCase.expected_output} onChange={(event) => updateTestCase(index, 'expected_output', event.target.value)} required />
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Input label="Marks" type="number" min="1" max="100" value={testCase.marks} onChange={(event) => updateTestCase(index, 'marks', event.target.value)} required className="max-w-28" />
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input type="checkbox" checked={testCase.is_sample} onChange={(event) => updateTestCase(index, 'is_sample', event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
                  Show as sample
                </label>
              </div>
            </div>
          ))}
          <p className={`text-right text-sm ${testCaseMarks === Number(question.total_marks) ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500'}`}>
            Test-case marks: {testCaseMarks} / {Number(question.total_marks) || 0}
          </p>
        </section>

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 dark:border-slate-800 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" onClick={close} disabled={saving}>Cancel</Button>
          <Button type="submit" loading={saving}><Save size={15} />Create and add question</Button>
        </div>
      </form>
    </Modal>
  );
};

export default QuestionCreateModal;
